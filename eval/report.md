# EKA Agent Evaluation Report

- Total cases: 15
- Runtime errors: 0/15
- Keyword grounding accuracy: 15/15 (100.0%)
- Tool-selection accuracy: 14/14 (100.0%)
- Out-of-scope flagging rate: 1/1 (100.0%)
- Citation presence on KB questions: 12/12 (100.0%)
- Latency: p50 2983ms / p95 14810ms

## By category

| Category | Cases | Keyword hit | Tool hit |
|---|---|---|---|
| grounded_fact | 11 | 11/11 | 11/11 |
| tool_selection | 2 | 2/2 | 2/2 |
| multi_hop | 1 | 1/1 | 1/1 |
| out_of_scope | 1 | 1/1 | - |

## Per-case detail

| ID | Category | Latency | KW | Tool | Flag | Cites | Answer (truncated) |
|---|---|---|---|---|---|---|---|
| legal-01 | grounded_fact | 3563ms | True | True | None | True | The monthly service fee in the service agreement is 45,000,000 VND [1]. |
| legal-02 | grounded_fact | 2636ms | True | True | None | True | The governing law that applies to the service agreement is the laws of Singapore |
| legal-03 | grounded_fact | 14810ms | True | True | None | True | The provider commits to a monthly uptime of 99.9% in the service agreement. If t |
| legal-04 | grounded_fact | 2847ms | True | True | None | True | The client has 30 days to cure a material breach after receiving written notice  |
| hr-01 | grounded_fact | 2983ms | True | True | None | True | Employees receive 12 annual leave days per year, with a maximum of 5 days that c |
| hr-02 | grounded_fact | 2689ms | True | True | None | True | The minimum required password length per the IT security policy is at least 12 c |
| hr-03 | grounded_fact | 3001ms | True | True | None | True | An employee can work remotely for a maximum of 3 days per week, with team lead a |
| hr-04 | grounded_fact | 2788ms | True | True | None | True | The daily meal expense limit while traveling is up to 250,000 VND per day [1]. |
| it-01 | grounded_fact | 2373ms | True | True | None | True | A SEV-1 incident must be acknowledged within 5 minutes [1]. |
| it-02 | grounded_fact | 3436ms | True | True | None | True | If a SEV-1 incident is still unresolved after 45 minutes, it escalates to the Ch |
| it-03 | grounded_fact | 3190ms | True | True | None | True | During a SEV-1 incident, status updates should be posted every 15 minutes [1]. |
| tool-calc-01 | tool_selection | 2064ms | True | True | None | False | The result of 128 times 6.5 is 832.0. |
| tool-list-01 | tool_selection | 4998ms | True | True | None | False | The following documents are currently available in the knowledge base:  1. **it_ |
| multi-hop-01 | multi_hop | 4545ms | True | True | None | True | Employees receive 12 annual leave days per year. If someone has used 7 of them,  |
| out-of-scope-01 | out_of_scope | 1391ms | True | None | True | False | This is not from the knowledge base; from general knowledge: The capital of Fran |