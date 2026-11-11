# Avaliação Automatizada de Usabilidade de Interfaces Web com LLMs

Este repositório contém o desenvolvimento de uma solução para avaliação automatizada de usabilidade de interfaces web utilizando **Modelos de Linguagem de Grande Escala (LLMs)**. O projeto faz parte de um Trabalho de Conclusão de Curso (TCC) em Ciência da Computação, no Centro de Informática da Universidade Federal de Pernambuco (CIn/UFPE).

## Sobre o Projeto

A avaliação de usabilidade é fundamental para identificar barreiras de interação e melhorar a experiência dos usuários em aplicações web. Entretanto, os métodos tradicionais frequentemente exigem tempo e participação de especialistas.

Este projeto investiga o uso de agentes baseados em LLMs para automatizar parte desse processo, comparando duas abordagens:

1. **Agente Genérico:** utiliza LLMs para avaliar interfaces web com base em princípios gerais de usabilidade, sem incorporar um método específico de análise cognitiva.

2. **Agente com GenderMag:** incorpora o método GenderMag para identificar barreiras de usabilidade relacionadas a diferentes características cognitivas e estratégias de interação dos usuários.

As duas abordagens serão aplicadas às mesmas interfaces e tarefas, permitindo uma comparação dos resultados.

## Objetivos

O objetivo principal é investigar como a incorporação do método GenderMag a agentes baseados em LLMs influencia sua capacidade de identificar problemas de usabilidade em interfaces web.

Os objetivos específicos incluem:

- Desenvolver agentes capazes de navegar e avaliar interfaces web.
- Integrar o método GenderMag a uma das abordagens de avaliação.
- Criar interfaces web controladas, contendo problemas de usabilidade previamente definidos e versões corrigidas.
- Executar experimentos utilizando as duas abordagens nas mesmas condições.
- Comparar os problemas identificados pelos agentes.
- Analisar a precisão, a cobertura e as limitações das avaliações automatizadas.

## Metodologia

O desenvolvimento e a avaliação experimental serão organizados em quatro etapas.

### 1. Desenvolvimento das Interfaces

Criação de interfaces web controladas, incluindo versões com problemas de usabilidade conhecidos e versões nas quais esses problemas foram corrigidos.

### 2. Desenvolvimento dos Agentes

Implementação de duas abordagens de avaliação: um agente genérico baseado em LLM e um agente orientado pelo método GenderMag.

### 3. Execução dos Experimentos

Realização de tarefas de interação previamente definidas, utilizando os dois agentes nas mesmas interfaces e em condições comparáveis.

### 4. Análise dos Resultados

Comparação dos problemas identificados pelos agentes com os problemas previamente definidos, considerando a capacidade de detecção, os falsos positivos e as diferenças entre as abordagens.

## Estrutura do Repositório

Estrutura inicial proposta, sujeita a alterações durante o desenvolvimento.

```text
llm-usability-evaluation/
├── agents/
│   ├── baseline/
│   └── gendermag/
├── interfaces/
│   ├── interface-01/
│   └── interface-02/
├── experiments/
├── results/
├── docs/
├── tests/
└── README.md
```

## Tecnologias

As tecnologias serão definidas ao longo do desenvolvimento. Inicialmente, estão previstas:

- **Python:** desenvolvimento dos agentes e execução dos experimentos.
- **LLMs:** análise automatizada das interfaces.
- **Automação de navegadores:** navegação e execução das tarefas.
- **HTML, CSS e JavaScript:** desenvolvimento das interfaces experimentais.
- **Ferramentas de análise de dados:** organização e comparação dos resultados.
