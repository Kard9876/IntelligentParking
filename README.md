# ASM

## Membros

- PG55932 Diogo Ferreira (DiogoUM)
- PG55946 Guilherme Barbosa (Kard9876)
- PG55959 João Carvalho (HiiceCream)
- PG55998 Rafael Peixoto (rafapeixoto16)
- PG56005 Rodrigo Ralha (rodrigo0345)

## Proposta

### Gestão de Parques de Estacionamento

- Diversos Parques
- Cada parque dividido em secções, cada uma supervisionada por um agente
- Cada parque com múltiplas entradas
- Cada parque com lugares especializados e lugares comuns
- Cada parque possui um gestor central

#### Estratégias de alocação

- Procurar o local mais próximo do destino do veículo, priorizando preferências e características do cliente
- Quando o parque está cheio, devemos ter em conta a distância e o custo de outros parques
- Cada parque tem um custo, o qual o cliente quer minimizar
- Cliente deve indicar qual a preferência do tipo de lugar

### Observações

- O sistema deve ser escalável com o número de clientes
- Os diversos parques não se conhecem entre si
