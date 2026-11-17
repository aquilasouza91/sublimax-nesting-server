# Sublimax Nesting Server

Servidor Python com Flask para cálculo de nesting de peças com contornos irregulares.

## 🚀 Deploy no Render.com

1. **Criar repositório no GitHub:**
   ```bash
   cd sublimax-nesting-server
   git init
   git add .
   git commit -m "initial commit: servidor de nesting"
   git branch -M main
   git remote add origin https://github.com/SEU-USUARIO/sublimax-nesting-server.git
   git push -u origin main
   ```

2. **Deploy automático no Render:**
   - Acessar https://render.com
   - Login com GitHub
   - New → Web Service
   - Conectar repositório `sublimax-nesting-server`
   - Render detecta automaticamente o `render.yaml`
   - Deploy automático!

## 📦 Estrutura

```
sublimax-nesting-server/
├── app.py              # API Flask principal
├── requirements.txt    # Dependências Python
├── render.yaml         # Configuração do Render.com
└── README.md           # Este arquivo
```

## 🔧 Algoritmo

**FFDH Melhorado com SAT (Separating Axis Theorem)**

- Usa contornos reais das peças (não retângulos)
- Detecção de colisão por polígono
- 4 rotações (0°, 90°, 180°, 270°)
- Grid de posicionamento com spacing configurável
- Múltiplas folhas

**Funções principais:**
- `parse_contour()` - Converte formato Desktop (|x,y;...) → pontos
- `polygons_overlap()` - SAT para detecção de colisão
- `nest_with_improved_ffdh()` - Algoritmo principal

## 📡 API

### `GET /health`

Health check.

**Response:**
```json
{
  "status": "ok",
  "service": "sublimax-nesting-server"
}
```

### `POST /nest`

Calcular nesting de peças.

**Request:**
```json
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
```

**Response:**
```json
{
  "success": true,
  "sheets": [
    {
      "index": 0,
      "parts": [
        {
          "id": "MATRIZ 2",
          "x": 0,
          "y": 0,
          "width": 647.99,
          "height": 855.14,
          "rotated": false,
          "rotation": 0
        }
      ]
    }
  ],
  "statistics": {
    "total_parts": 1,
    "placed_parts": 1,
    "total_area": 553925.7,
    "sheet_area": 32000000,
    "used_sheets": 1,
    "efficiency": 1.73,
    "waste_percentage": 98.27
  }
}
```

## 🧪 Testar Localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar servidor
python app.py

# Testar endpoint
curl -X POST http://localhost:10000/nest \
  -H "Content-Type: application/json" \
  -d '{
    "parts": [{
      "id": "test",
      "width": 100,
      "height": 200,
      "contour": "|10000,20000;10000,0;0,0;0,20000;10000,20000",
      "quantity": 1,
      "rotation": true
    }],
    "sheet_width": 1600,
    "sheet_height": 2000,
    "spacing": 2
  }'
```

## 🔗 Integração com Lovable

No Lovable (`encaixe.calcular.ts`):

```typescript
const nestingResponse = await fetch(
  'https://sublimax-nesting.onrender.com/nest',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(nestingPayload),
  }
);
```

## 📊 Performance

- **Tempo:** 2-5s para 26 peças
- **Aproveitamento esperado:** 40-60% (vs 23% do FFDH simples)
- **Limitação:** Grid step de 10mm (trade-off velocidade vs precisão)

## 🛠️ Melhorias Futuras

- [ ] Algoritmo genético para otimização
- [ ] NFP (No Fit Polygon) real
- [ ] Part-in-part (peças dentro de buracos)
- [ ] Cache de cálculos
- [ ] WebSocket para progresso em tempo real

---

**Versão:** 1.0.0  
**Autor:** Kiro AI  
**Licença:** MIT
