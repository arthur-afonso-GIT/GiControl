from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtCharts import QChart, QChartView, QPieSeries
from PySide6.QtGui import QPainter, QColor
from datetime import datetime

class DashboardView(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # ================= CARDS SUPERIORES =================
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_balance = self._create_card("SALDO ATUAL GERAL (ACUMULADO)", "R$ 0,00", "#ffffff")
        self.card_income = self._create_card("RECEITAS DO MÊS", "R$ 0,00", "#00b37e")
        self.card_expense = self._create_card("DESPESAS DO MÊS", "R$ 0,00", "#f75a68")
        self.card_savings = self._create_card("ECONOMIA NO MÊS", "R$ 0,00", "#00b37e")

        cards_layout.addWidget(self.card_balance)
        cards_layout.addWidget(self.card_income)
        cards_layout.addWidget(self.card_expense)
        cards_layout.addWidget(self.card_savings)
        main_layout.addLayout(cards_layout)

        # ================= CONTEÚDO INFERIOR: TABELA (ESQUERDA) E GRÁFICO (DIREITA) =================
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)

        # Container da Tabela de Últimas Movimentações
        table_container = QWidget()
        table_vbox = QVBoxLayout(table_container)
        table_vbox.setContentsMargins(0, 0, 0, 0)
        table_vbox.setSpacing(10)

        lbl_table_title = QLabel("Últimas Movimentações")
        lbl_table_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        table_vbox.addWidget(lbl_table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Data", "Descrição", "Tipo", "Valor"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setStyleSheet("""
            QTableWidget { 
                background-color: #19191d; 
                border: 1px solid #29292e; 
                border-radius: 8px; 
            }
        """)
        table_vbox.addWidget(self.table)
        bottom_layout.addWidget(table_container, stretch=3)

        # Container do Gráfico
        chart_container = QFrame()
        chart_container.setStyleSheet("background-color: #19191d; border: 1px solid #29292e; border-radius: 8px;")
        chart_vbox = QVBoxLayout(chart_container)
        chart_vbox.setContentsMargins(16, 16, 16, 16)
        chart_vbox.setSpacing(10)

        lbl_chart_title = QLabel("Distribuição de Despesas")
        lbl_chart_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; border: none;")
        chart_vbox.addWidget(lbl_chart_title)

        # Inicialização do QChart nativo
        self.chart = QChart()
        self.chart.setBackgroundVisible(False)
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignBottom)
        self.chart.legend().setLabelColor(QColor("#a8a8b3"))

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setStyleSheet("background: transparent; border: none;")
        
        chart_vbox.addWidget(self.chart_view)
        bottom_layout.addWidget(chart_container, stretch=2)

        main_layout.addLayout(bottom_layout, stretch=1)

        self.update_view_data()

    def _create_card(self, title, initial_value, value_color):
        card = QFrame()
        card.setStyleSheet("background-color: #19191d; border: 1px solid #29292e; border-radius: 8px;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #71717a; border: none;")
        
        lbl_value = QLabel(initial_value)
        lbl_value.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {value_color}; border: none;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        
        # Guardamos a referência do label para atualizar o texto dinamicamente depois
        card.lbl_value = lbl_value 
        return card

    def update_view_data(self):
        """Puxa dados calculados do Core, atualiza os cards, preenche a tabela e redesenha o gráfico."""
        metrics = self.manager.get_dashboard_metrics()

        # 1. Atualiza os cards
        self.card_balance.lbl_value.setText(f"R$ {metrics['current_balance']:.2f}")
        self.card_income.lbl_value.setText(f"R$ {metrics['monthly_income']:.2f}")
        self.card_expense.lbl_value.setText(f"R$ {metrics['monthly_expense']:.2f}")
        self.card_savings.lbl_value.setText(f"R$ {metrics['savings']:.2f}")

        if metrics['savings'] >= 0:
            self.card_savings.lbl_value.setStyleSheet("font-size: 24px; font-weight: bold; color: #00b37e; border: none;")
        else:
            self.card_savings.lbl_value.setStyleSheet("font-size: 24px; font-weight: bold; color: #f75a68; border: none;")

        # 2. Atualiza a tabela de transações recentes
        recent = metrics["recent_transactions"]
        self.table.setRowCount(len(recent))
        
        for row, t in enumerate(recent):
            # Formata a data de YYYY-MM-DD para DD/MM/YYYY
            date_obj = datetime.strptime(t["date"], "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d/%m/%Y")

            item_date = QTableWidgetItem(formatted_date)
            item_desc = QTableWidgetItem(t["description"])
            item_type = QTableWidgetItem(t["type"])
            
            if t["type"] == "Receita":
                item_val = QTableWidgetItem(f"+ R$ {t['amount']:.2f}")
                item_val.setForeground(QColor("#00b37e"))
            else:
                item_val = QTableWidgetItem(f"- R$ {t['amount']:.2f}")
                item_val.setForeground(QColor("#f75a68"))

            item_date.setTextAlignment(Qt.AlignCenter)
            item_type.setTextAlignment(Qt.AlignCenter)
            item_val.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self.table.setItem(row, 0, item_date)
            self.table.setItem(row, 1, item_desc)
            self.table.setItem(row, 2, item_type)
            self.table.setItem(row, 3, item_val)

        # 3. Atualiza e reconstrói o gráfico de rosca baseado em despesas reais por categoria
        self.chart.removeAllSeries()
        
        # Dicionário auxiliar para mapear as cores da paleta Rocket nas fatias
        color_palette = ["#00b37e", "#f75a68", "#8257e5", "#ff9000", "#3383ff", "#e02041"]
        
        # Consolida gastos por categorias do mês corrente
        categories = self.manager.get_categories()
        cat_map = {c["id"]: c["name"] for c in categories if c["type"] == "Despesa"}
        expenses_by_cat = {}

        current_month = datetime.now().strftime("%Y-%m")
        for t in self.manager.get_transactions():
            if t["date"].startswith(current_month) and t["type"] == "Despesa":
                cat_name = cat_map.get(t["category_id"], "Outros")
                expenses_by_cat[cat_name] = expenses_by_cat.get(cat_name, 0.0) + t["amount"]

        if expenses_by_cat:
            series = QPieSeries()
            # Transforma o gráfico de pizza em Rosca (Donut) abrindo o meio
            series.setHoleSize(0.45) 
            
            for idx, (cat_name, value) in enumerate(expenses_by_cat.items()):
                slice_ = series.append(f"{cat_name} (R$ {value:.2f})", value)
                # Atribui cor da paleta para combinar com o tema dark
                color_idx = idx % len(color_palette)
                slice_.setBrush(QColor(color_palette[color_idx]))
                slice_.setBorderColor(QColor("#19191d"))
                slice_.setLabelVisible(False) # Evita poluição visual, dependendo apenas da legenda inferior
                
            self.chart.addSeries(series)
        else:
            # Gráfico vazio de espera caso não haja gastos registrados no mês
            series = QPieSeries()
            series.setHoleSize(0.45)
            slice_empty = series.append("Sem despesas no mês", 1)
            slice_empty.setBrush(QColor("#29292e"))
            slice_empty.setBorderColor(QColor("#19191d"))
            self.chart.addSeries(series)

    def update_data(self):
        """Mantém compatibilidade com chamadas anteriores ao contrato padronizado."""
        self.update_view_data()
