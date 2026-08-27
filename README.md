# GiControl - Gestão Financeira Pessoal

GiControl é uma aplicação de gestão financeira pessoal com frontend React, API FastAPI e persistência SQLite. Durante a transição arquitetural, a interface desktop PySide6 permanece disponível como caminho de compatibilidade.

---

## 📸 Screenshots

### Main Dashboard & Overview
*Real-time charts, total balance summary, and modern statistics.*
<img width="1918" height="1015" alt="image" src="https://github.com/user-attachments/assets/36c85b42-da50-4cff-b6a8-0e03eeae244b" />


### Transaction Management View
*Clean layout featuring an organized transactions history table and a premium, responsive side-form protected against UI clipping and distortion in Full-Screen mode.*
<img width="1918" height="1005" alt="image" src="https://github.com/user-attachments/assets/7b4fee57-766a-4ec5-aef0-5d27cea40c02" />


### Categories
<img width="1918" height="1021" alt="image" src="https://github.com/user-attachments/assets/06ad8878-33c7-482d-8909-d816360041cb" />

### Accounts Management
<img width="1918" height="1017" alt="image" src="https://github.com/user-attachments/assets/70b059e4-288b-4a85-87eb-291342c4cd98" />

---

## 🚀 Features

- **Transaction Ledger:** Clear overview of expenses and incomes with automatic color-coding (Red for Expenses, Green for Income).
- **Responsive Form Layout:** Premium input form built using `QFormLayout` to prevent visual deformation, ensuring crystal-clear text fields and labels in both windowed and full-screen modes.
- **Dynamic Data Syncing:** Real-time updates automatically recalculate balances and switch layouts flawlessly.
- **Safe Records Removal:** Double-click interaction on any transaction item with a modal confirmation box to safely update bank data and views.
- **Advanced Controls:** Support for categorizing expenses, linking transactions to specific payment accounts, tracking installments, and recurring fixed expenses.

---

## 🛠️ Technology Stack

- **Language:** Python 3.10+
- **GUI Framework:** PySide6 (Qt for Python)
- **Style Engine:** Qt Style Sheets (QSS / CSS Custom Dark Mode)
- **Database Architecture:** SQLite (via internal manager component)

---

## 📦 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/your-username/fincontrol.git](https://github.com/your-username/fincontrol.git)
   cd fincontrol
