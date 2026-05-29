**Here is the complete content for your `SKILL.md` file**, ready to copy and paste:

---

```markdown
# Skill: get_client_data

## Description
This skill retrieves basic registration data of clients.

## When to use this skill
Use this skill when the agent needs one or more of the following client data:
- `cnpj_cpf`
- `codigo_cliente`
- `nome_fantasia`
- `razao_social`

## Input Parameters
**None**  
This skill does not accept any parameters. It always returns the full list of clients.

## Output Format
The skill returns data in **JSON Lines** format (one JSON object per line), with the following fields:

```json
{
  "cnpj_cpf": "15.470.976/0001-03",
  "codigo_cliente": 6216003967,
  "codigo_cliente_integracao": "",
  "nome_fantasia": "CONSTRUALTO",
  "razao_social": "JR MATERIAIS DE CONSTRUCAO LTDA"
}
```

## Execution
The agent must execute the following script when this skill is used:
```
scripts/list_client_data.py
```
