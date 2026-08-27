from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QFormLayout, QFrame, QMessageBox, 
    QListWidget, QListWidgetItem, QDoubleSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy

class CategoriesView(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.current_editing_id = None  # Guarda o ID se estiver editando uma categoria
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(24)

        # =====================================================================
        # ESQUERDA: LISTAGEM DE CATEGORIAS
        # =====================================================================
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        title_box = QHBoxLayout()
        title = QLabel("Divisão por Categorias")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        tip = QLabel("(1 clique p/ editar • 2 cliques p/ remover)")
        tip.setStyleSheet("font-size: 12px; color: #a8a8b3; font-style: italic; padding-top: 10px;")
        title_box.addWidget(title)
        title_box.addWidget(tip)
        title_box.addStretch()
        left_layout.addLayout(title_box)

        lists_layout = QHBoxLayout()
        lists_layout.setSpacing(16)

        # Coluna de Despesas
        expense_box = QVBoxLayout()
        lbl_exp = QLabel("Categorias de Despesa")
        lbl_exp.setStyleSheet("font-size: 14px; font-weight: bold; color: #f75a68;")
        
        self.list_expenses = QListWidget()
        self.list_expenses.setStyleSheet("""
            QListWidget { background-color: #19191d; border: 1px solid #29292e; border-radius: 8px; padding: 8px; color: #ffffff; font-size: 14px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #202024; }
            QListWidget::item:selected { background-color: #29292e; color: #00b37e; border: none; }
        """)
        # Conecta os cliques individuais e duplos
        self.list_expenses.itemClicked.connect(self.load_category_for_edit)
        self.list_expenses.itemDoubleClicked.connect(self.delete_category_clicked)
        
        expense_box.addWidget(lbl_exp)
        expense_box.addWidget(self.list_expenses)

        # Coluna de Receitas
        income_box = QVBoxLayout()
        lbl_inc = QLabel("Categorias de Receita")
        lbl_inc.setStyleSheet("font-size: 14px; font-weight: bold; color: #00b37e;")
        
        self.list_incomes = QListWidget()
        self.list_incomes.setStyleSheet("""
            QListWidget { background-color: #19191d; border: 1px solid #29292e; border-radius: 8px; padding: 8px; color: #ffffff; font-size: 14px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #202024; }
            QListWidget::item:selected { background-color: #29292e; color: #00b37e; border: none; }
        """)
        # Conecta os cliques individuais e duplos
        self.list_incomes.itemClicked.connect(self.load_category_for_edit)
        self.list_incomes.itemDoubleClicked.connect(self.delete_category_clicked)
        
        income_box.addWidget(lbl_inc)
        income_box.addWidget(self.list_incomes)

        lists_layout.addLayout(expense_box)
        lists_layout.addLayout(income_box)
        left_layout.addLayout(lists_layout)
        
        main_layout.addWidget(left_container, stretch=3)

        # =====================================================================
        # DIREITA: PAINEL DE CADASTRO / EDIÇÃO E METAS
        # =====================================================================
        right_panel = QFrame()
        right_panel.setFixedWidth(360)
        right_panel.setStyleSheet("""
            QFrame { background-color: #19191d; border: 1px solid #29292e; border-radius: 8px; }
            QLabel { border: none; color: #a8a8b3; font-size: 13px; }
            QLineEdit, QComboBox, QDoubleSpinBox {
                background-color: #202024; border: 1px solid #29292e;
                border-radius: 6px; padding: 10px; color: #ffffff;
            }
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus { border: 1px solid #00b37e; }
        """)
        
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(16)

        self.form_title = QLabel("Configurar Categoria")
        self.form_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff; border: none; margin-bottom: 10px;")
        right_layout.addWidget(self.form_title)

        form = QFormLayout()
        form.setSpacing(15)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Ex: Lazer, Streaming, Bônus...")
        self.txt_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.cb_type = QComboBox()
        self.cb_type.addItems(["Despesa", "Receita"])
        self.cb_type.currentTextChanged.connect(self._toggle_limit_field)
        self.cb_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.txt_limit = QDoubleSpinBox()
        self.txt_limit.setRange(0.00, 999999.99)
        self.txt_limit.setPrefix("Meta: R$ ")
        self.txt_limit.setSpecialValueText("Sem Teto Definido")
        self.txt_limit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        form.addRow("Nome:", self.txt_name)
        form.addRow("Tipo:", self.cb_type)
        self.lbl_limit_row = QLabel("Teto de Gastos:")
        form.addRow(self.lbl_limit_row, self.txt_limit)
        right_layout.addLayout(form)

        self.btn_save = QPushButton("Salvar Alterações")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #00b37e; color: #ffffff; font-weight: bold;
                border: none; border-radius: 6px; padding: 12px; font-size: 14px;
            }
            QPushButton:hover { background-color: #00875f; }
        """)
        self.btn_save.clicked.connect(self.save_category)
        right_layout.addWidget(self.btn_save)

        # Botão para cancelar edição e voltar ao modo de nova categoria
        self.btn_cancel = QPushButton("Cancelar Edição")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton { background-color: #29292e; color: #a8a8b3; border: none; border-radius: 6px; padding: 8px; font-size: 12px; }
            QPushButton:hover { color: #ffffff; background-color: #323238; }
        """)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.clear_form)
        right_layout.addWidget(self.btn_cancel)

        right_layout.addStretch()
        main_layout.addWidget(right_panel)

        self.update_view_data()

    def _toggle_limit_field(self, current_text):
        visible = current_text == "Despesa"
        self.txt_limit.setVisible(visible)
        self.lbl_limit_row.setVisible(visible)

    def update_view_data(self):
        """Força a sincronização com o JSON e redesenha as listas armazenando os IDs em segundo plano."""
        self.list_expenses.clear()
        self.list_incomes.clear()

        categories = self.manager.get_categories()
        
        for cat in categories:
            limit = cat.get("monthly_limit", 0.0)
            if cat["type"] == "Despesa" and limit > 0:
                text = f"{cat['name']}  (Meta: R$ {limit:,.2f})"
            else:
                text = cat["name"]

            item = QListWidgetItem(text)
            # Injeta o id real da categoria no item da lista
            item.setData(Qt.UserRole, cat["id"])

            if cat["type"] == "Despesa":
                self.list_expenses.addItem(item)
            else:
                self.list_incomes.addItem(item)

    def load_category_for_edit(self, item):
        """1 CLIQUE: Carrega a categoria selecionada no formulário da direita para edição."""
        category_id = item.data(Qt.UserRole)
        categories = self.manager.get_categories()
        
        # Encontra a categoria correspondente no banco
        cat = next((c for c in categories if c["id"] == category_id), None)
        if cat:
            self.current_editing_id = cat["id"]
            self.txt_name.setText(cat["name"])
            self.cb_type.setCurrentText(cat["type"])
            self.txt_limit.setValue(cat.get("monthly_limit", 0.0))
            
            # Muda os textos do painel para indicar o modo Edição
            self.form_title.setText("Editar Categoria")
            self.btn_save.setText("Atualizar Categoria")
            self.btn_cancel.setVisible(True)

    def delete_category_clicked(self, item):
        """2 CLIQUES: Pergunta se deseja remover a categoria selecionada."""
        category_id = item.data(Qt.UserRole)
        categories = self.manager.get_categories()
        cat = next((c for c in categories if c["id"] == category_id), None)
        
        if not cat:
            return

        reply = QMessageBox.question(
            self, "Remover Categoria",
            f"Tem certeza que deseja apagar a categoria '{cat['name']}'?\n"
            "As transações vinculadas a ela não serão apagadas, mas ficarão sem categoria.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = self.manager.delete_category(category_id)

            if success:
                self.clear_form()
                self.update_view_data()
                
                # Sincroniza com as outras telas do app (Dashboard, Transações)
                main_window = self.window()
                if hasattr(main_window, "refresh_all_views"):
                    main_window.refresh_all_views()
            else:
                QMessageBox.critical(self, "Erro", "Não foi possível remover a categoria.")

    def clear_form(self):
        """Reseta o formulário da direita para o modo padrão (Novo cadastro)."""
        self.current_editing_id = None
        self.txt_name.clear()
        self.txt_limit.setValue(0.0)
        self.form_title.setText("Configurar Categoria")
        self.btn_save.setText("Salvar Alterações")
        self.btn_cancel.setVisible(False)
        self.list_expenses.clearSelection()
        self.list_incomes.clearSelection()

    def save_category(self):
        """Processa a gravação (Criar nova ou Atualizar existente)."""
        name = self.txt_name.text().strip()
        cat_type = self.cb_type.currentText()
        limit = self.txt_limit.value() if cat_type == "Despesa" else 0.0

        if not name:
            QMessageBox.warning(self, "Erro", "Defina um nome para a categoria.")
            return

        if self.current_editing_id:
            self.manager.update_category(
                self.current_editing_id,
                name,
                cat_type,
                limit,
            )
        else:
            # MODO CADASTRO: Adiciona uma nova normalmente
            self.manager.add_category(name, cat_type, limit)
        
        # Feedback, limpa os campos e propaga a atualização para o app inteiro
        self.clear_form()
        self.update_view_data()
        
        main_window = self.window()
        if hasattr(main_window, "refresh_all_views"):
            main_window.refresh_all_views()
