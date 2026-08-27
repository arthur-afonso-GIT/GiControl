from copy import deepcopy


_DEFAULT_DATA = {
    "accounts": [],
    "categories": [
        {"id": "1", "name": "Alimentação", "type": "Despesa", "monthly_limit": 0.0},
        {"id": "2", "name": "Transporte", "type": "Despesa", "monthly_limit": 0.0},
        {"id": "3", "name": "Saúde", "type": "Despesa", "monthly_limit": 0.0},
        {"id": "4", "name": "Salário", "type": "Receita", "monthly_limit": 0.0},
        {"id": "5", "name": "Investimentos", "type": "Receita", "monthly_limit": 0.0},
    ],
    "transactions": [],
}


def default_data() -> dict:
    return deepcopy(_DEFAULT_DATA)
