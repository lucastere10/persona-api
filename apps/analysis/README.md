# Analysis App - Initial Data Analysis

Esta aplicação Django fornece endpoints simplificados para análise inicial de dados, focando em facilidade de uso e funcionalidades essenciais.

## Visão Geral

A aplicação foi refatorada para:
- **Simplicidade**: Apenas 3 endpoints essenciais
- **Facilidade de uso**: Sem necessidade de autenticação JWT
- **Foco claro**: Análise inicial/simplificada de dados
- **Código limpo**: Remoção de funcionalidades desnecessárias

## Estrutura da Aplicação

```
apps/analysis/
├── models.py              # Modelo AnalysisResult
├── views.py               # Views simplificadas (Initial Analysis)
├── urls.py                # URLs para análise inicial
├── serializers.py         # Serializers para API
├── admin.py               # Interface administrativa
├── services/              # Serviços de análise
│   ├── comprehensive_analysis.py  # Serviço principal
│   ├── file_reader.py            # Leitura de arquivos
│   ├── data_analysis.py          # Análise de dados
│   ├── data_profiler.py          # Profiling de dados
│   ├── data_cleaner.py           # Limpeza de dados
│   ├── openai_api_request.py     # Integração OpenAI
│   └── backup/                   # Serviços antigos (backup)
├── backup_files/          # Arquivos antigos removidos
└── INITIAL_ANALYSIS_API.md # Documentação da API
```

## Endpoints Disponíveis

### 1. Submeter Análise
- **URL**: `POST /api/analysis/initial-analysis/`
- **Autenticação**: Não necessária
- **Função**: Submete arquivo para análise

### 2. Obter Resultados
- **URL**: `GET /api/analysis/initial-analysis/{id}/`
- **Autenticação**: Access token via header
- **Função**: Recupera resultados completos

### 3. Listar Análises
- **URL**: `GET /api/analysis/initial-analysis-list/`
- **Autenticação**: Não necessária
- **Função**: Lista análises com paginação

## Modelo de Dados

### AnalysisResult
- `id`: UUID único
- `access_token`: Token de acesso seguro
- `file_name`: Nome do arquivo original
- `sheet_name`: Nome da planilha (Excel)
- `use_ai`: Se usou insights de IA
- `results`: Resultados completos (JSON)
- `created_at/updated_at`: Timestamps

## Funcionalidades

### Análise Suportada
- **Formatos**: CSV, Excel (.xls/.xlsx), TSV, TXT
- **Profiling**: Análise completa dos dados
- **Limpeza**: Configurável via JSON
- **IA**: Insights opcionais via OpenAI
- **Segurança**: Access tokens únicos

### Recursos Removidos
- Endpoints de profiling separado
- Endpoints de limpeza separado
- Testes de API OpenAI standalone
- Autenticação JWT obrigatória
- Documentação de uso complexa

## Configuração

### Dependências Principais
- Django REST Framework
- pandas, numpy (análise de dados)
- ydata-profiling (profiling)
- openpyxl (Excel)
- OpenAI (opcional, para insights)

### Variáveis de Ambiente
```bash
OPENAI_API_KEY=your_openai_key  # Opcional para insights IA
```

## Uso Rápido

### 1. Submeter Arquivo
```bash
curl -X POST \
  http://localhost:8000/api/analysis/initial-analysis/ \
  -F "file=@dados.csv" \
  -F "use_ai=true"
```

### 2. Obter Resultados
```bash
curl -X GET \
  http://localhost:8000/api/analysis/initial-analysis/{id}/ \
  -H "access-token: {token}"
```

### 3. Listar Análises
```bash
curl -X GET \
  "http://localhost:8000/api/analysis/initial-analysis-list/?page=1"
```

## Administração

Acesso via Django Admin:
- Visualizar análises realizadas
- Filtrar por arquivo, data, uso de IA
- Ver resumos e resultados completos

## Logs e Debugging

- Logs estruturados para análises
- Rastreamento de erros
- Métricas de performance

## Migração de Versões Anteriores

Se você usava endpoints antigos:
- `comprehensive-analysis` → `initial-analysis`
- Remoção de autenticação JWT obrigatória
- Mesmo formato de dados de resposta
- Access tokens mantidos para segurança

## Desenvolvimento

Para desenvolvimento local:
1. Configure o ambiente virtual
2. Instale dependências: `pip install -r requirements.txt`
3. Execute migrações: `python manage.py migrate`
4. Inicie servidor: `python manage.py runserver`

## Testes

Execute testes da aplicação:
```bash
python manage.py test apps.analysis
```

## Suporte

Para dúvidas sobre a API, consulte:
- `INITIAL_ANALYSIS_API.md` - Documentação completa da API
- `services/README.md` - Documentação dos serviços
- Django Admin - Interface administrativa
