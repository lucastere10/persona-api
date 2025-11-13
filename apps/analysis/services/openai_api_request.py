"""
OpenAI API Request Service

This service handles communication with OpenAI's API for data analysis
and natural language processing tasks.
"""

import openai
import json
import logging
from decouple import config
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class OpenAIService:
    """
    Service for interacting with OpenAI's API for data analysis tasks.
    """
    
    def __init__(self):
        self.api_key = config('OPEN_API')  # Using OPEN_API from settings
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        self.default_model = "gpt-3.5-turbo"
    
    def generate_data_analysis_insights(self, health_check: Dict, cleaning_report: Dict) -> Dict[str, Any]:
        """
        Generate insights about data quality and cleaning results using OpenAI.
        
        Args:
            health_check: Health check results from DataProfiler
            cleaning_report: Cleaning report from DataCleaner
            
        Returns:
            Dict: AI-generated insights and recommendations
        """
        try:
            # Prepare context for AI analysis
            context = self._prepare_analysis_context(health_check, cleaning_report)
            
            prompt = f"""
            Analise os resultados de qualidade e limpeza dos dados fornecidos. 
            Seja objetivo, preciso e forneça análises estruturadas.

            INFORMAÇÕES DO DATASET:
            {context}

            Responda EXCLUSIVAMENTE em formato JSON válido seguindo esta estrutura exata:
            {{
                "avaliacao_geral": {{
                    "nota_qualidade": 8.5,
                    "percentual_completude": 92.3,
                    "nivel_confianca": "ALTO",
                    "resumo": "Breve resumo da qualidade geral (máximo 150 caracteres)"
                }},
                "metricas_qualidade": {{
                    "dados_faltantes_pct": 7.7,
                    "duplicatas_pct": 0.5,
                    "colunas_problematicas": 3,
                    "tipos_dados_inconsistentes": 1
                }},
                "principais_achados": [
                    "Achado objetivo e específico 1",
                    "Achado objetivo e específico 2",
                    "Achado objetivo e específico 3"
                ],
                "problemas_identificados": [
                    {{
                        "categoria": "DADOS_FALTANTES|DUPLICATAS|OUTLIERS|TIPOS_DADOS|FORMATACAO|CONSISTENCIA",
                        "descricao": "Descrição clara e específica do problema",
                        "severidade": "CRITICA|ALTA|MEDIA|BAIXA",
                        "impacto": "Impacto específico na análise"
                    }}
                ],
                "recomendacoes_acao": [
                    {{
                        "prioridade": "ALTA|MEDIA|BAIXA",
                        "categoria": "LIMPEZA|VALIDACAO|TRANSFORMACAO|EXPLORACAO",
                        "acao": "Ação específica e prática a ser executada",
                        "justificativa": "Por que esta ação é necessária"
                    }}
                ],
                "adequacao_analises": {{
                    "estatistica_descritiva": "ADEQUADO|PARCIAL|INADEQUADO",
                    "machine_learning": "ADEQUADO|PARCIAL|INADEQUADO",
                    "visualizacao": "ADEQUADO|PARCIAL|INADEQUADO",
                    "observacoes": "Comentários sobre adequação para diferentes tipos de análise"
                }},
                "proximos_passos": [
                    "Passo imediato e específico 1",
                    "Passo imediato e específico 2"
                ]
            }}
            
            CRITÉRIOS DE AVALIAÇÃO:
            - Nota 9-10: Dados excelentes, prontos para análise
            - Nota 7-8: Dados bons, necessitam limpeza mínima
            - Nota 5-6: Dados regulares, necessitam tratamento significativo
            - Nota 3-4: Dados ruins, requerem limpeza extensiva
            - Nota 1-2: Dados muito ruins, podem ser inadequados para análise
            """
            
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista sênior em qualidade de dados e ciência de dados. Forneça análises objetivas, técnicas e acionáveis sobre qualidade de dados. Use sempre português brasileiro, seja preciso com números e métricas, e foque em insights práticos para tomada de decisão. Responda apenas no formato JSON solicitado, sem texto adicional."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.2  # Lower temperature for more focused analysis
            )
            
            # Extract the response
            analysis = response.choices[0].message.content
            
            # Parse token usage
            tokens_used = response.usage
            
            result = {
                "analysis": analysis,
                "token_usage": {
                    "prompt_tokens": tokens_used.prompt_tokens,
                    "completion_tokens": tokens_used.completion_tokens,
                    "total_tokens": tokens_used.total_tokens
                },
                "model_used": self.default_model,
                "success": True
            }
            
            logger.info(f"Generated data analysis insights using {tokens_used.total_tokens} tokens")
            return result
            
        except Exception as e:
            logger.error(f"Error generating data analysis insights: {e}")
            return {
                "error": str(e),
                "success": False
            }
    
    def explain_data_patterns(self, column_analysis: Dict, column_name: str) -> Dict[str, Any]:
        """
        Use AI to explain patterns found in a specific column in Brazilian Portuguese.
        
        Args:
            column_analysis: Analysis results for a specific column
            column_name: Name of the column being analyzed
            
        Returns:
            Dict: AI explanation of the column patterns
        """
        try:
            prompt = f"""
            Analise a coluna "{column_name}" e explique os padrões encontrados:

            ANÁLISE DA COLUNA:
            - Tipo de dados: {column_analysis.get('data_type', 'Desconhecido')}
            - Valores únicos: {column_analysis.get('unique_count', 'Desconhecido')}
            - Valores faltantes: {column_analysis.get('missing_percentage', 0):.1f}%
            - Percentual único: {column_analysis.get('unique_percentage', 0):.1f}%
            
            Detalhes adicionais: {json.dumps(column_analysis, indent=2, default=str)}

            Retorne APENAS JSON válido seguindo esta estrutura:
            {{
                "interpretacao_coluna": {{
                    "tipo_provavel": "Categoria da coluna (ID, texto, numérico, categórico, temporal, etc.)",
                    "proposito_negocio": "Provável propósito desta coluna no contexto de negócio",
                    "qualidade_dados": "EXCELENTE|BOA|REGULAR|RUIM|MUITO_RUIM"
                }},
                "observacoes_qualidade": [
                    "Observação específica sobre qualidade 1",
                    "Observação específica sobre qualidade 2"
                ],
                "anomalias_detectadas": [
                    "Anomalia específica detectada 1",
                    "Anomalia específica detectada 2"
                ],
                "recomendacoes_tratamento": [
                    {{
                        "acao": "Ação específica para tratamento",
                        "justificativa": "Por que esta ação é necessária",
                        "prioridade": "ALTA|MEDIA|BAIXA"
                    }}
                ],
                "adequacao_uso": {{
                    "analise_estatistica": "ADEQUADA|PARCIAL|INADEQUADA",
                    "machine_learning": "ADEQUADA|PARCIAL|INADEQUADA",
                    "visualizacao": "ADEQUADA|PARCIAL|INADEQUADA",
                    "observacoes": "Comentários sobre uso da coluna"
                }}
            }}
            """
            
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista em análise de dados que explica padrões de colunas de forma técnica e objetiva. Use português brasileiro e seja específico sobre qualidade e tratamento de dados. Responda apenas no formato JSON solicitado."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            explanation = response.choices[0].message.content
            tokens_used = response.usage
            
            result = {
                "column_name": column_name,
                "explanation": explanation,
                "token_usage": {
                    "prompt_tokens": tokens_used.prompt_tokens,
                    "completion_tokens": tokens_used.completion_tokens,
                    "total_tokens": tokens_used.total_tokens
                },
                "success": True
            }
            
            logger.info(f"Generated column explanation for '{column_name}' using {tokens_used.total_tokens} tokens")
            return result
            
        except Exception as e:
            logger.error(f"Error explaining column patterns for '{column_name}': {e}")
            return {
                "error": str(e),
                "success": False
            }
    
    def suggest_analysis_approach(self, dataset_summary: Dict) -> Dict[str, Any]:
        """
        Get AI suggestions for analysis approach based on dataset characteristics in Brazilian Portuguese.
        
        Args:
            dataset_summary: Summary of dataset characteristics
            
        Returns:
            Dict: AI suggestions for analysis approach
        """
        try:
            prompt = f"""
            Com base nas características do dataset, sugira uma abordagem de análise apropriada:

            RESUMO DO DATASET:
            - Formato: {dataset_summary.get('shape', 'Desconhecido')}
            - Número de colunas: {dataset_summary.get('column_count', 'Desconhecido')}
            - Tipos de dados: {dataset_summary.get('data_types', {})}
            - Percentual de dados faltantes: {dataset_summary.get('missing_percentage', 0):.1f}%
            - Possui duplicatas: {dataset_summary.get('has_duplicates', False)}
            
            Contexto adicional: {json.dumps(dataset_summary, indent=2, default=str)}

            Retorne APENAS JSON válido seguindo esta estrutura:
            {{
                "tipo_analise_recomendada": {{
                    "categoria_principal": "EXPLORATORIA|PREDITIVA|DESCRITIVA|PRESCRITIVA|DIAGNOSTICA",
                    "subcategorias": ["Subcategoria 1", "Subcategoria 2"],
                    "justificativa": "Por que esta abordagem é recomendada"
                }},
                "visualizacoes_sugeridas": [
                    {{
                        "tipo": "Tipo de gráfico/visualização",
                        "proposito": "Para que serve esta visualização",
                        "prioridade": "ALTA|MEDIA|BAIXA"
                    }}
                ],
                "metodos_estatisticos": [
                    {{
                        "metodo": "Nome do método estatístico",
                        "aplicacao": "Como aplicar ao dataset",
                        "requisitos": "Pré-requisitos para aplicação"
                    }}
                ],
                "adequacao_ml": {{
                    "adequado": true,
                    "tipos_ml_recomendados": ["Tipo 1", "Tipo 2"],
                    "preparacao_necessaria": ["Preparação 1", "Preparação 2"],
                    "observacoes": "Observações sobre uso de ML"
                }},
                "questoes_negocio": [
                    "Questão de negócio específica que pode ser respondida 1",
                    "Questão de negócio específica que pode ser respondida 2",
                    "Questão de negócio específica que pode ser respondida 3"
                ],
                "proximos_passos_analise": [
                    {{
                        "ordem": 1,
                        "atividade": "Atividade específica a ser realizada",
                        "tempo_estimado": "Estimativa de tempo",
                        "recursos_necessarios": ["Recurso 1", "Recurso 2"]
                    }}
                ]
            }}
            """
            
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um consultor sênior em ciência de dados que fornece orientação estratégica sobre abordagens de análise de dados. Use português brasileiro, seja específico e prático nas recomendações. Responda apenas no formato JSON solicitado."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1200,
                temperature=0.4
            )
            
            suggestions = response.choices[0].message.content
            tokens_used = response.usage
            
            result = {
                "suggestions": suggestions,
                "token_usage": {
                    "prompt_tokens": tokens_used.prompt_tokens,
                    "completion_tokens": tokens_used.completion_tokens,
                    "total_tokens": tokens_used.total_tokens
                },
                "success": True
            }
            
            logger.info(f"Generated analysis approach suggestions using {tokens_used.total_tokens} tokens")
            return result
            
        except Exception as e:
            logger.error(f"Error generating analysis approach suggestions: {e}")
            return {
                "error": str(e),
                "success": False
            }
    
    def analyze_ml_readiness(self, dataset_info: Dict, target_column: str = None) -> Dict[str, Any]:
        """
        Analyze dataset readiness for machine learning applications.
        
        Args:
            dataset_info: Comprehensive dataset information
            target_column: Optional target column for supervised learning
            
        Returns:
            Dict: ML readiness analysis
        """
        try:
            target_info = f"Coluna alvo especificada: {target_column}" if target_column else "Nenhuma coluna alvo especificada (análise não supervisionada)"
            
            prompt = f"""
            Analise a adequação deste dataset para aplicações de machine learning:

            INFORMAÇÕES DO DATASET:
            {json.dumps(dataset_info, indent=2, default=str)}
            
            {target_info}

            Retorne APENAS JSON válido seguindo esta estrutura:
            {{
                "adequacao_geral": {{
                    "nota_ml": 7.5,
                    "nivel": "EXCELENTE|BOA|REGULAR|RUIM|INADEQUADA",
                    "resumo": "Resumo da adequação para ML"
                }},
                "problemas_ml": [
                    {{
                        "categoria": "DADOS_FALTANTES|DESBALANCEAMENTO|DIMENSIONALIDADE|QUALIDADE|OUTLIERS",
                        "descricao": "Descrição específica do problema",
                        "impacto_ml": "Como afeta modelos de ML",
                        "severidade": "CRITICA|ALTA|MEDIA|BAIXA"
                    }}
                ],
                "tipos_ml_adequados": [
                    {{
                        "categoria": "SUPERVISIONADO|NAO_SUPERVISIONADO|SEMI_SUPERVISIONADO|REINFORCEMENT",
                        "algoritmos_recomendados": ["Algoritmo 1", "Algoritmo 2"],
                        "justificativa": "Por que estes algoritmos são adequados"
                    }}
                ],
                "preparacao_necessaria": [
                    {{
                        "etapa": "Nome da etapa de preparação",
                        "atividades": ["Atividade 1", "Atividade 2"],
                        "prioridade": "ALTA|MEDIA|BAIXA",
                        "complexidade": "SIMPLES|MODERADA|COMPLEXA"
                    }}
                ],
                "metricas_avaliacao": {{
                    "metricas_recomendadas": ["Métrica 1", "Métrica 2"],
                    "estrategia_validacao": "Estratégia de validação recomendada",
                    "consideracoes_especiais": "Considerações especiais para avaliação"
                }},
                "riscos_limitacoes": [
                    "Risco ou limitação específica 1",
                    "Risco ou limitação específica 2"
                ],
                "cronograma_estimado": {{
                    "preparacao_dados": "X dias/semanas",
                    "desenvolvimento_modelo": "X dias/semanas",
                    "validacao_teste": "X dias/semanas",
                    "total_estimado": "X dias/semanas"
                }}
            }}
            """
            
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista em machine learning que avalia adequação de datasets para projetos de ML. Seja técnico, objetivo e forneça estimativas realistas. Use português brasileiro e responda apenas no formato JSON solicitado."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1500,
                temperature=0.2
            )
            
            analysis = response.choices[0].message.content
            tokens_used = response.usage
            
            result = {
                "ml_analysis": analysis,
                "target_column": target_column,
                "token_usage": {
                    "prompt_tokens": tokens_used.prompt_tokens,
                    "completion_tokens": tokens_used.completion_tokens,
                    "total_tokens": tokens_used.total_tokens
                },
                "success": True
            }
            
            logger.info(f"Generated ML readiness analysis using {tokens_used.total_tokens} tokens")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing ML readiness: {e}")
            return {
                "error": str(e),
                "success": False
            }
    
    def _prepare_analysis_context(self, health_check: Dict, cleaning_report: Dict) -> str:
        """
        Prepare detailed context string for AI analysis in Brazilian Portuguese.
        
        Args:
            health_check: Health check results
            cleaning_report: Cleaning report
            
        Returns:
            str: Formatted context for AI analysis
        """
        context_parts = []
        
        # Add basic dataset information
        self._add_basic_info(context_parts, health_check)
        
        # Add missing data information
        self._add_missing_data_info(context_parts, health_check)
        
        # Add data quality information
        self._add_data_quality_info(context_parts, health_check)
        
        # Add cleaning results
        self._add_cleaning_results(context_parts, cleaning_report)
        
        # Add recommendations
        self._add_recommendations(context_parts, health_check)
        
        return '\n'.join(context_parts)
    
    def _add_basic_info(self, context_parts: list, health_check: Dict):
        """Add basic dataset information to context."""
        if 'data_shape' in health_check:
            shape = health_check['data_shape']
            context_parts.append(f"📊 Dimensões do Dataset: {shape[0]:,} linhas × {shape[1]} colunas")
        
        if 'memory_usage_mb' in health_check:
            memory_mb = health_check['memory_usage_mb']
            if memory_mb > 1024:
                context_parts.append(f"💾 Uso de Memória: {memory_mb:.1f} MB ({memory_mb/1024:.2f} GB)")
            else:
                context_parts.append(f"💾 Uso de Memória: {memory_mb:.1f} MB")
        
        self._add_data_types_info(context_parts, health_check)
    
    def _add_data_types_info(self, context_parts: list, health_check: Dict):
        """Add data types information to context."""
        if 'data_types' in health_check:
            types_info = health_check['data_types']
            if isinstance(types_info, dict):
                type_counts = {}
                for col, dtype in types_info.items():
                    type_counts[str(dtype)] = type_counts.get(str(dtype), 0) + 1
                type_summary = ", ".join([f"{count} {dtype}" for dtype, count in type_counts.items()])
                context_parts.append(f"🔤 Tipos de Dados: {type_summary}")
    
    def _add_missing_data_info(self, context_parts: list, health_check: Dict):
        """Add missing data information to context."""
        missing_data = health_check.get('missing_data', {})
        if not missing_data:
            return
        
        total_missing = missing_data.get('total_missing_values', 0)
        columns_with_missing = missing_data.get('columns_with_missing', {})
        
        shape = health_check.get('data_shape', [0, 0])
        total_cells = shape[0] * shape[1]
        missing_pct = (total_missing / total_cells * 100) if total_cells > 0 else 0
        
        context_parts.append(f"❌ Dados Faltantes: {total_missing:,} valores ({missing_pct:.1f}% do total)")
        context_parts.append(f"📋 Colunas Afetadas: {len(columns_with_missing)} de {shape[1]} colunas")
        
        if columns_with_missing:
            worst_columns = sorted(columns_with_missing.items(), key=lambda x: x[1], reverse=True)[:3]
            worst_info = ", ".join([f"{col} ({pct:.1f}%)" for col, pct in worst_columns])
            context_parts.append(f"🚨 Colunas Mais Problemáticas: {worst_info}")
    
    def _add_data_quality_info(self, context_parts: list, health_check: Dict):
        """Add data quality information to context."""
        data_quality = health_check.get('data_quality', {})
        if not data_quality:
            return
        
        self._add_duplicate_info(context_parts, data_quality, health_check)
        self._add_column_issues(context_parts, data_quality)
    
    def _add_duplicate_info(self, context_parts: list, data_quality: Dict, health_check: Dict):
        """Add duplicate rows information."""
        duplicate_rows = data_quality.get('duplicate_rows', 0)
        if duplicate_rows > 0:
            total_rows = health_check.get('data_shape', [0, 0])[0]
            dup_pct = (duplicate_rows / total_rows * 100) if total_rows > 0 else 0
            context_parts.append(f"🔄 Linhas Duplicadas: {duplicate_rows:,} ({dup_pct:.1f}%)")
    
    def _add_column_issues(self, context_parts: list, data_quality: Dict):
        """Add column-related issues information."""
        constant_columns = data_quality.get('constant_columns', [])
        high_cardinality = data_quality.get('high_cardinality_columns', [])
        
        if constant_columns:
            context_parts.append(f"⚠️ Colunas Constantes: {len(constant_columns)} colunas sem variação")
        
        if high_cardinality:
            context_parts.append(f"📈 Alta Cardinalidade: {len(high_cardinality)} colunas com muitos valores únicos")
    
    def _add_cleaning_results(self, context_parts: list, cleaning_report: Dict):
        """Add cleaning results information to context."""
        if not cleaning_report or 'cleaning_summary' not in cleaning_report:
            return
        
        summary = cleaning_report['cleaning_summary']
        cols_removed = summary.get('columns_removed_count', 0)
        rows_removed = summary.get('rows_removed_count', 0)
        data_reduction = summary.get('data_reduction_percentage', 0)
        
        context_parts.append("🧹 Resultados da Limpeza:")
        if cols_removed > 0:
            context_parts.append(f"  • Colunas removidas: {cols_removed}")
        if rows_removed > 0:
            context_parts.append(f"  • Linhas removidas: {rows_removed:,}")
        if data_reduction > 0:
            context_parts.append(f"  • Redução total: {data_reduction:.1f}%")
    
    def _add_recommendations(self, context_parts: list, health_check: Dict):
        """Add recommendations to context."""
        recommendations = health_check.get('recommendations', [])
        if not recommendations:
            return
        
        context_parts.append("💡 Recomendações Principais:")
        for i, rec in enumerate(recommendations[:3], 1):
            context_parts.append(f"  {i}. {rec}")
        
        # Add statistical summary if available
        if 'statistical_summary' in health_check:
            stats = health_check['statistical_summary']
            if stats:
                context_parts.append(f"📈 Resumo Estatístico Disponível: {len(stats)} colunas analisadas")
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the OpenAI API connection.
        
        Returns:
            Dict: Connection test results
        """
        try:
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {
                        "role": "user",
                        "content": "Teste de conexão. Responda apenas com 'Conexão bem-sucedida!' em português brasileiro."
                    }
                ],
                max_tokens=10
            )
            
            reply = response.choices[0].message.content
            tokens_used = response.usage
            
            return {
                "success": True,
                "message": reply,
                "token_usage": {
                    "prompt_tokens": tokens_used.prompt_tokens,
                    "completion_tokens": tokens_used.completion_tokens,
                    "total_tokens": tokens_used.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Teste de conexão OpenAI falhou: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Legacy function for backward compatibility
def test_openai_connection():
    """
    Simple function to test OpenAI API connection.
    """
    service = OpenAIService()
    return service.test_connection()


if __name__ == "__main__":
    # Test the service
    service = OpenAIService()
    result = service.test_connection()
    
    if result['success']:
        print("✅ OpenAI connection successful!")
        print(f"Response: {result['message']}")
        print(f"Tokens used: {result['token_usage']['total_tokens']}")
    else:
        print("❌ OpenAI connection failed!")
        print(f"Error: {result['error']}")


