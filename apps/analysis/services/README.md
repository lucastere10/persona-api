# Analysis Services Documentation

Esta pasta contém os serviços essenciais para análise inicial/simplificada de dados.

## Serviços Disponíveis

### 1. File Reader Service (`file_reader.py`)

Responsável pela leitura de diversos formatos de arquivo com detecção inteligente e validação.

**Formatos Suportados:**
- CSV (com detecção automática de delimitador)
- Excel (.xls, .xlsx, .xlsm) com suporte a múltiplas planilhas
- Arquivos de texto (.txt, .tsv)
- Detecção automática de encoding

**Principais Funcionalidades:**
- Detecção automática do tipo de arquivo
- Enumeração de planilhas Excel
- Detecção e tratamento de encoding
- Validação de dados
- Tratamento abrangente de erros

### 2. Data Profiler Service (`data_profiler.py`)

Fornece profiling abrangente de dados usando `ydata_profiling` e verificações customizadas de qualidade.

**Principais Funcionalidades:**
- Profiling completo com ydata_profiling
- Análise de health check
- Análise de dados faltantes
- Avaliação de qualidade dos dados
- Análise coluna por coluna
- Recomendações automáticas

### 3. Data Cleaner Service (`data_cleaner.py`)

Serviço de limpeza de dados com configurações personalizáveis.

**Principais Funcionalidades:**
- Remoção de valores faltantes
- Detecção e tratamento de outliers
- Remoção de duplicatas
- Normalização de dados
- Configuração flexível via JSON

### 4. Comprehensive Analysis Service (`comprehensive_analysis.py`)

Serviço principal que orquestra todo o workflow de análise, incluindo:
- Carregamento e validação de dados
- Profiling de dados
- Limpeza de dados (opcional)
- Insights com IA (opcional)
- Geração de resultados estruturados

### 5. OpenAI API Service (`openai_api_request.py`)

Serviço para integração com OpenAI para fornecer insights e recomendações inteligentes.

**Principais Funcionalidades:**
- Geração de insights sobre dados
- Análise de padrões
- Recomendações de limpeza
- Sugestões de abordagens de análise
- Avaliação de adequação para ML

## Uso Principal

O ponto de entrada principal para análise é através do `ComprehensiveAnalysisService` que orquestra todos os serviços necessários para um workflow completo de análise.

```python
from apps.analysis.services.comprehensive_analysis import ComprehensiveAnalysisService

# Inicializar serviço
service = ComprehensiveAnalysisService(use_openai=True)

# Executar análise
results = service.analyze_file(file_path, sheet_name=None, cleaning_config=None)
```

## Endpoints da API

A aplicação fornece endpoints simplificados:
- `POST /initial-analysis/` - Submeter arquivo para análise inicial
- `GET /initial-analysis/<id>/` - Recuperar resultados da análise
- `GET /initial-analysis-list/` - Listar todas as análises com paginação

Todos os endpoints são publicamente acessíveis (sem autenticação JWT obrigatória) para facilitar integração e testes.

## Dependências

- **pandas, numpy**: Manipulação e análise de dados
- **ydata-profiling**: Profiling avançado de dados
- **openpyxl**: Leitura de arquivos Excel
- **scikit-learn**: Algoritmos de ML para limpeza
- **openai**: Integração com OpenAI (opcional)

## Configuração

### Variáveis de Ambiente
```bash
OPENAI_API_KEY=sua_chave_openai  # Opcional para insights com IA
```

### Exemplo de Uso
```python
# 1. Leitura de arquivo
from apps.analysis.services.file_reader import read_data_file
data, info = read_data_file(file_obj, filename)

# 2. Profiling
from apps.analysis.services.data_profiler import DataProfiler
profiler = DataProfiler()
profile_results = profiler.profile_dataframe(data)

# 3. Limpeza
from apps.analysis.services.data_cleaner import DataCleaner
cleaner = DataCleaner()
cleaned_data = cleaner.clean_dataframe(data, config)

# 4. Análise completa (recomendado)
from apps.analysis.services.comprehensive_analysis import ComprehensiveAnalysisService
service = ComprehensiveAnalysisService(use_openai=True)
results = service.analyze_file(file_path)
```
