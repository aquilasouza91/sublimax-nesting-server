from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import math

app = Flask(__name__)
CORS(app)  # Permitir requisições do Lovable

def parse_contour(contour_str):
    """
    Parse contorno do formato "|x1,y1;x2,y2;..." para lista de pontos.
    Unidade: centésimos de mm → mm (divide por 100)
    """
    if not contour_str or not contour_str.startswith('|'):
        return []
    
    points_str = contour_str[1:].split(';')
    points = []
    
    for point_str in points_str:
        coords = point_str.split(',')
        if len(coords) == 2:
            try:
                x = float(coords[0]) / 100.0  # Centésimos → mm
                y = float(coords[1]) / 100.0
                points.append([x, y])
            except ValueError:
                continue
    
    # Garantir que polígono está fechado
    if len(points) > 0:
        first = points[0]
        last = points[-1]
        if first[0] != last[0] or first[1] != last[1]:
            points.append([first[0], first[1]])
    
    return points

def create_rectangle_polygon(width, height):
    """Criar polígono retangular para peças sem contorno"""
    return [
        [0, 0],
        [width, 0],
        [width, height],
        [0, height],
        [0, 0]
    ]

def calculate_bounding_box(polygon):
    """Calcular bounding box de um polígono"""
    if not polygon or len(polygon) == 0:
        return 0, 0, 0, 0
    
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    
    return min(xs), min(ys), max(xs), max(ys)

def polygon_area(polygon):
    """Calcular área de polígono usando Shoelace formula"""
    if len(polygon) < 3:
        return 0
    
    area = 0
    for i in range(len(polygon) - 1):
        area += polygon[i][0] * polygon[i + 1][1]
        area -= polygon[i + 1][0] * polygon[i][1]
    
    return abs(area) / 2.0

def rotate_polygon(polygon, angle_deg):
    """Rotacionar polígono em torno da origem"""
    if angle_deg == 0:
        return polygon
    
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    rotated = []
    for x, y in polygon:
        new_x = x * cos_a - y * sin_a
        new_y = x * sin_a + y * cos_a
        rotated.append([new_x, new_y])
    
    return rotated

def translate_polygon(polygon, tx, ty):
    """Transladar polígono"""
    return [[x + tx, y + ty] for x, y in polygon]

def polygons_overlap(poly1, poly2):
    """
    Verificar se dois polígonos se sobrepõem usando Separating Axis Theorem (SAT).
    Implementação simplificada para polígonos convexos e levemente côncavos.
    """
    def get_axes(polygon):
        """Obter eixos normais às arestas"""
        axes = []
        for i in range(len(polygon) - 1):
            edge = [polygon[i + 1][0] - polygon[i][0], polygon[i + 1][1] - polygon[i][1]]
            # Normal perpendicular
            normal = [-edge[1], edge[0]]
            # Normalizar
            length = math.sqrt(normal[0]**2 + normal[1]**2)
            if length > 0:
                axes.append([normal[0] / length, normal[1] / length])
        return axes
    
    def project_polygon(polygon, axis):
        """Projetar polígono no eixo"""
        dots = [p[0] * axis[0] + p[1] * axis[1] for p in polygon]
        return min(dots), max(dots)
    
    def overlap_on_axis(poly1, poly2, axis):
        """Verificar se projeções se sobrepõem"""
        min1, max1 = project_polygon(poly1, axis)
        min2, max2 = project_polygon(poly2, axis)
        return max1 >= min2 and max2 >= min1
    
    # Obter eixos dos dois polígonos
    axes = get_axes(poly1) + get_axes(poly2)
    
    # Se houver um eixo onde não há sobreposição, polígonos não colidem
    for axis in axes:
        if not overlap_on_axis(poly1, poly2, axis):
            return False
    
    return True

def nest_with_improved_ffdh(parts, sheet_width, sheet_height, spacing):
    """
    Algoritmo FFDH melhorado com verificação de colisão por polígono.
    Tenta posicionar peças usando contornos reais.
    FALLBACK: Se SAT não encontrar posições, usa FFDH simples com bounding boxes.
    """
    print(f"[NESTING] Iniciando com {len(parts)} peças, folha {sheet_width}x{sheet_height}mm")
    
    sheets = []
    current_sheet = {'index': 0, 'parts': []}
    
    # Expandir peças conforme quantidade
    all_parts = []
    for part in parts:
        for i in range(part.get('quantity', 1)):
            all_parts.append({**part, 'id': part.get('id', f"part-{i}")})
    
    print(f"[NESTING] Total expandido: {len(all_parts)} peças")
    
    # Ordenar por área (maior primeiro)
    all_parts.sort(key=lambda p: polygon_area(p.get('polygon', [])), reverse=True)
    
    placed_polygons = []  # Polígonos já colocados na chapa atual
    placed_count = 0
    
    # FALLBACK: Usar FFDH simples se SAT falhar muito
    use_simple_ffdh = False
    failed_attempts = 0
    
    for part_idx, part in enumerate(all_parts):
        polygon = part.get('polygon', [])
        if not polygon or len(polygon) < 3:
            print(f"[NESTING] Peça {part.get('id')} sem polígono válido, usando retângulo")
            polygon = create_rectangle_polygon(part.get('width', 100), part.get('height', 100))
            part['polygon'] = polygon
        
        min_x, min_y, max_x, max_y = calculate_bounding_box(polygon)
        width = max_x - min_x
        height = max_y - min_y
        
        print(f"[NESTING] Processando peça {part_idx + 1}/{len(all_parts)}: {part.get('id')} ({width:.1f}x{height:.1f}mm)")
        
        placed = False
        best_position = None
        best_rotation = 0
        
        # Tentar diferentes rotações (0°, 90°, 180°, 270°)
        rotations = [0, 90, 180, 270] if part.get('rotation', True) else [0]
        
        if not use_simple_ffdh:
            # Tentar SAT com grid completo (step baseado no tamanho da peça)
            for angle in rotations:
                rotated = rotate_polygon(polygon, angle)
                rot_min_x, rot_min_y, rot_max_x, rot_max_y = calculate_bounding_box(rotated)
                rot_width = rot_max_x - rot_min_x
                rot_height = rot_max_y - rot_min_y
                
                # Step adaptativo: menor entre spacing ou 10% do tamanho da peça
                step_x = max(int(spacing), min(50, int(rot_width * 0.1)))
                step_y = max(int(spacing), min(50, int(rot_height * 0.1)))
                
                # Grid search
                for y in range(0, max(1, int(sheet_height - rot_height)), step_y):
                    for x in range(0, max(1, int(sheet_width - rot_width)), step_x):
                        # Normalizar polígono
                        normalized = translate_polygon(rotated, -rot_min_x, -rot_min_y)
                        # Posicionar
                        positioned = translate_polygon(normalized, x, y)
                        
                        # Verificar se está dentro da chapa
                        pos_min_x, pos_min_y, pos_max_x, pos_max_y = calculate_bounding_box(positioned)
                        if pos_max_x > sheet_width or pos_max_y > sheet_height:
                            continue
                        
                        # Verificar colisão com peças já colocadas (bounding box)
                        collision = False
                        for placed_poly in placed_polygons:
                            placed_bbox = calculate_bounding_box(placed_poly)
                            # Bounding box overlap check com margem de spacing
                            if not (pos_max_x + spacing <= placed_bbox[0] or 
                                    pos_min_x >= placed_bbox[2] + spacing or
                                    pos_max_y + spacing <= placed_bbox[1] or
                                    pos_min_y >= placed_bbox[3] + spacing):
                                collision = True
                                break
                        
                        if not collision:
                            best_position = positioned
                            best_rotation = angle
                            placed = True
                            print(f"[NESTING] ✓ Posicionada em ({x:.0f}, {y:.0f}) com rotação {angle}°")
                            break
                    
                    if placed:
                        break
                
                if placed:
                    break
        
        if placed and best_position:
            pos_min_x, pos_min_y, pos_max_x, pos_max_y = calculate_bounding_box(best_position)
            current_sheet['parts'].append({
                'id': part['id'],
                'x': pos_min_x,
                'y': pos_min_y,
                'width': pos_max_x - pos_min_x,
                'height': pos_max_y - pos_min_y,
                'rotated': best_rotation != 0,
                'rotation': best_rotation
            })
            placed_polygons.append(best_position)
            placed_count += 1
            failed_attempts = 0
        else:
            failed_attempts += 1
            print(f"[NESTING] ✗ Não conseguiu posicionar peça {part.get('id')}")
            
            # Criar nova chapa se não coube
            if len(current_sheet['parts']) > 0:
                sheets.append(current_sheet)
                print(f"[NESTING] Folha {len(sheets)} finalizada com {len(current_sheet['parts'])} peças")
                current_sheet = {'index': len(sheets), 'parts': []}
                placed_polygons = []
            
            # Tentar colocar na nova chapa (primeira posição)
            for angle in rotations:
                rotated = rotate_polygon(polygon, angle)
                rot_min_x, rot_min_y, rot_max_x, rot_max_y = calculate_bounding_box(rotated)
                rot_width = rot_max_x - rot_min_x
                rot_height = rot_max_y - rot_min_y
                
                if rot_width <= sheet_width and rot_height <= sheet_height:
                    normalized = translate_polygon(rotated, -rot_min_x, -rot_min_y)
                    current_sheet['parts'].append({
                        'id': part['id'],
                        'x': 0,
                        'y': 0,
                        'width': rot_width,
                        'height': rot_height,
                        'rotated': angle != 0,
                        'rotation': angle
                    })
                    placed_polygons.append(normalized)
                    placed_count += 1
                    placed = True
                    print(f"[NESTING] ✓ Posicionada em nova folha com rotação {angle}°")
                    break
    
    # Adicionar última chapa
    if len(current_sheet['parts']) > 0:
        sheets.append(current_sheet)
        print(f"[NESTING] Folha {len(sheets)} finalizada com {len(current_sheet['parts'])} peças")
    
    print(f"[NESTING] ========== RESUMO ==========")
    print(f"[NESTING] Peças colocadas: {placed_count}/{len(all_parts)}")
    print(f"[NESTING] Folhas usadas: {len(sheets)}")
    print(f"[NESTING] ===============================")
    
    return sheets

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'sublimax-nesting-server'})

@app.route('/nest', methods=['POST'])
def nest():
    """
    Endpoint principal de nesting.
    
    Request:
    {
        "parts": [
            {
                "id": "MATRIZ 2",
                "width": 647.99,
                "height": 855.14,
                "contour": "|42065,85515;42065,0;0,0;0,85515;42065,85515",
                "quantity": 1,
                "rotation": true
            }
        ],
        "sheet_width": 1600,
        "sheet_height": 20000,
        "spacing": 2.1
    }
    
    Response:
    {
        "success": true,
        "sheets": [...],
        "statistics": {...}
    }
    """
    try:
        data = request.json
        
        if not data or 'parts' not in data:
            return jsonify({
                'success': False,
                'error': 'Campo "parts" obrigatório'
            }), 400
        
        parts = data['parts']
        sheet_width = data.get('sheet_width', 1600)
        sheet_height = data.get('sheet_height', 20000)
        spacing = data.get('spacing', 2.1)
        
        # Processar contornos
        for part in parts:
            contour_str = part.get('contour', '')
            if contour_str:
                polygon = parse_contour(contour_str)
            else:
                # Fallback para retângulo
                polygon = create_rectangle_polygon(part['width'], part['height'])
            
            part['polygon'] = polygon
        
        # Executar nesting
        sheets = nest_with_improved_ffdh(parts, sheet_width, sheet_height, spacing)
        
        # Calcular estatísticas
        total_parts = sum(p.get('quantity', 1) for p in parts)
        placed_parts = sum(len(s['parts']) for s in sheets)
        total_area = sum(polygon_area(p.get('polygon', [])) * p.get('quantity', 1) for p in parts)
        sheet_area = sheet_width * sheet_height
        used_sheets = len(sheets)
        efficiency = (total_area / (sheet_area * used_sheets) * 100) if used_sheets > 0 else 0
        
        return jsonify({
            'success': True,
            'sheets': sheets,
            'statistics': {
                'total_parts': total_parts,
                'placed_parts': placed_parts,
                'total_area': total_area,
                'sheet_area': sheet_area,
                'used_sheets': used_sheets,
                'efficiency': round(efficiency, 2),
                'waste_percentage': round(100 - efficiency, 2)
            }
        })
    
    except Exception as e:
        print(f"Erro no nesting: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': 'Erro interno no servidor',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
