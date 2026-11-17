from flask import Flask, request, jsonify
from flask_cors import CORS
import rectpack

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'sublimax-nesting-simple'})

@app.route('/nest', methods=['POST'])
def nest():
    """Nesting simples usando rectpack (retângulos)"""
    try:
        data = request.json
        parts = data.get('parts', [])
        sheet_width = data.get('sheet_width', 1600)
        sheet_height = data.get('sheet_height', 2000)
        spacing = data.get('spacing', 2)
        
        print(f"[NESTING] Recebidas {len(parts)} peças")
        print(f"[NESTING] Folha: {sheet_width}x{sheet_height}mm, spacing: {spacing}mm")
        
        # Criar bins (folhas)
        packer = rectpack.newPacker(rotation=True)
        
        # Adicionar peças ao packer
        for i, part in enumerate(parts):
            width = int(part['width'] + spacing)
            height = int(part['height'] + spacing)
            packer.add_rect(width, height, rid=i)
            print(f"[NESTING] Peça {i}: {part.get('id')} {width}x{height}mm")
        
        # Adicionar bins ilimitados
        for _ in range(100):  # Máximo 100 folhas
            packer.add_bin(sheet_width, sheet_height)
        
        # Executar packing
        packer.pack()
        
        # Processar resultados
        sheets = []
        for bin_index, bin_rects in enumerate(packer):
            if not bin_rects:
                continue
                
            sheet_parts = []
            for rect in bin_rects:
                part_index = rect.rid
                part = parts[part_index]
                
                sheet_parts.append({
                    'id': part.get('id', f'part-{part_index}'),
                    'x': float(rect.x),
                    'y': float(rect.y),
                    'width': float(rect.width - spacing),
                    'height': float(rect.height - spacing),
                    'rotated': rect.width == int(part['height'] + spacing),
                    'rotation': 90 if rect.width == int(part['height'] + spacing) else 0
                })
            
            sheets.append({
                'index': bin_index,
                'parts': sheet_parts
            })
            print(f"[NESTING] Folha {bin_index + 1}: {len(sheet_parts)} peças")
        
        # Calcular eficiência
        total_part_area = sum(p['width'] * p['height'] for p in parts)
        total_sheet_area = len(sheets) * sheet_width * sheet_height
        efficiency = (total_part_area / total_sheet_area * 100) if total_sheet_area > 0 else 0
        
        print(f"[NESTING] Total: {len(sheets)} folhas, {efficiency:.1f}% aproveitamento")
        
        return jsonify({
            'success': True,
            'sheets': sheets,
            'efficiency': efficiency,
            'total_parts': len(parts),
            'placed_parts': sum(len(s['parts']) for s in sheets)
        })
        
    except Exception as e:
        print(f"[NESTING] ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'sheets': []
        }), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
