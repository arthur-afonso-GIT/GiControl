from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QStackedWidget, QFrame, QLabel
)
from PySide6.QtCore import Qt

# Importação das telas de visualização
from views.dashboard_view import DashboardView
from views.transactions_view import TransactionsView
from views.accounts_view import AccountsView
from views.categories_view import CategoriesView

class MainWindow(QMainWindow):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        
        self.setWindowTitle("GiControl - Gerenciador Financeiro")
        self.resize(1200, 750)
        
        self._setup_ui()

    def _setup_ui(self):
        # Janela central com fundo escuro padrão do seu app
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #121214; color: #ffffff;")
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # =====================================================================
        # BARRA LATERAL (MENU DE NAVEGAÇÃO)
        # =====================================================================
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #19191d;
                border-right: 1px solid #29292e;
            }
            QPushButton {
                background-color: transparent;
                color: #a8a8b3;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #202024;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #29292e;
                color: #00b37e;
            }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(8)

        logo = QLabel("GiControl")
        logo.setStyleSheet("font-size: 22px; font-weight: bold; color: #00b37e; margin-bottom: 24px; padding-left: 8px;")
        sidebar_layout.addWidget(logo)

        # Grupo de botões do menu
        self.btn_dashboard = QPushButton("  Dashboard")
        self.btn_dashboard.setCheckable(True)
        self.btn_dashboard.setChecked(True)
        
        self.btn_transactions = QPushButton("  Histórico / Gastos")
        self.btn_transactions.setCheckable(True)
        
        self.btn_categories = QPushButton("  Categorias")
        self.btn_categories.setCheckable(True)
        
        self.btn_accounts = QPushButton("  Contas")
        self.btn_accounts.setCheckable(True)

        sidebar_layout.addWidget(self.btn_dashboard)
        sidebar_layout.addWidget(self.btn_transactions)
        sidebar_layout.addWidget(self.btn_categories)
        sidebar_layout.addWidget(self.btn_accounts)
        sidebar_layout.addStretch()

        # Vincula cliques das abas
        self.btn_dashboard.clicked.connect(lambda: self.switch_tab(0))
        self.btn_transactions.clicked.connect(lambda: self.switch_tab(1))
        self.btn_categories.clicked.connect(lambda: self.switch_tab(2))
        self.btn_accounts.clicked.connect(lambda: self.switch_tab(3))

        main_layout.addWidget(sidebar)

        # =====================================================================
        # ÁREA CENTRAL DE CONTEÚDO (STACKED WIDGET)
        # =====================================================================
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("padding: 32px;")

        self.view_dashboard = DashboardView(self.manager)
        self.view_transactions = TransactionsView(self.manager)
        self.view_categories = CategoriesView(self.manager)
        self.view_accounts = AccountsView(self.manager)

        self.content_stack.addWidget(self.view_dashboard)
        self.content_stack.addWidget(self.view_transactions)
        self.content_stack.addWidget(self.view_categories)
        self.content_stack.addWidget(self.view_accounts)

        main_layout.addWidget(self.content_stack)

    def switch_tab(self, index):
        """Alterna a tela ativa e garante a atualização de dados em tempo real."""
        self.content_stack.setCurrentIndex(index)
        
        self.btn_dashboard.setChecked(index == 0)
        self.btn_transactions.setChecked(index == 1)
        self.btn_categories.setChecked(index == 2)
        self.btn_accounts.setChecked(index == 3)

        if index == 0:
            self.view_dashboard.update_view_data()
        elif index == 1:
            self.view_transactions.update_view_data()
        elif index == 2:
            self.view_categories.update_view_data()
        elif index == 3:
            self.view_accounts.update_view_data()

    def refresh_all_views(self):
        """Força todas as telas a se atualizarem com o JSON atualizado."""
        self.view_dashboard.update_view_data()
        self.view_transactions.update_view_data()
        self.view_categories.update_view_data()
        self.view_accounts.update_view_data()
