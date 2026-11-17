from flask import Flask, request, jsonify
from flask_cors import CORS
from genetic_nesting import GeneticNesting

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'sublimax-nesting-simple'})

@app.route('/nest', methods=['POST'])
def nest():
    """Nesting usando Algoritmo Genético (baseado no eCut)"""
    try:
        data = request.json
        parts = data.get('parts', [])
        sheet_width = data.get('sheet_width', 1600)
        sheet_height = data.get('sheet_height', 2000)
        spacing = data.get('spacing', 2)
        genetics_time = data.get('genetics_time', 10)  # Tempo do algoritmo genético
        
        print(f"[NESTING] ========== ALGORITMO GENÉTICO ==========")
        print(f"[NESTING] Recebidas {len(parts)} peças")
        print(f"[NESTING] Folha: {sheet_width}x{sheet_height}mm")
        print(f"[NESTING] Spacing: {spacing}mm")
        print(f"[NESTING] Genetics Time: {genetics_time}s")
        
        # Criar instância do algoritmo genético
        genetic = GeneticNesting(
            sheet_width=sheet_width,
            sheet_height=sheet_height,
            spacing=spacing,
            genetics_time=genetics_time,
            genetics_check=3,
            population_size=100
        )
        
        # Executar algoritmo genético
        sheets = genetic.run(parts)
        
        # Calcular eficiência
        total_part_area = sum(p['width'] * p['height'] for p in parts)
        placed_parts = sum(len(s['parts']) for s in sheets)
        total_sheet_area = len(sheets) * sheet_width * sheet_height if sheets else 1
        efficiency = (total_part_area / total_sheet_area * 100) if total_sheet_area > 0 else 0
        
        print(f"[NESTING] ========== RESULTADO ==========")
        print(f"[NESTING] Folhas: {len(sheets)}")
        print(f"[NESTING] Peças colocadas: {placed_parts}/{len(parts)}")
        print(f"[NESTING] Eficiência: {efficiency:.1f}%")
        print(f"[NESTING] ===================================")
        
        return jsonify({
            'success': True,
            'sheets': sheets,
            'efficiency': efficiency,
            'total_parts': len(parts),
            'placed_parts': placed_parts
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
