###############################################################################
##   GUI  Y  LÓGICA   DE    PROGRAMACIÓN    DE     LA     VISTA    UserView  ##
###############################################################################
import sqlite3

# Importamos las librerías de carga y Widgets de Python QT v5
# para graficar el contenido de los ficheros GUI
from PyQt5 import uic, QtWebEngineWidgets
from PyQt5.QtWidgets import *

# Importamos la lógica de otras vistas
from highstock import Highstock

from src.View.AddCarterasView import AddCarterasView
from src.View.AddISINView import AddISINView
from src.util import fundUtils
from src.util.dialogs import *


'''
    - Ventana de Operaciones General para el Usuario 
    - En ella se podrán añadir Carteras, Fondos a Cada Una de ellas,
     así como graficar los Fondos seleccionados.
     
     @parent: MainView
     @children: AddAny | MainView
'''
# Vista PrincipalUsuario.ui
class UserView(QMainWindow):

    def __init__(view, parent=QMainWindow):
        super().__init__(parent)
        # Carga de la interfaz gráfica
        uic.loadUi("src/GUI/PrincipalUsuario.ui", view)

        # Conexión con la BD y creación de un cursor de consultas
        db_connection = sqlite3.connect('DemoData.db', isolation_level=None)
        db = db_connection.cursor()

        # Captura del Usuario a través de la vista parent (MainView - LoginView)
        usuario = parent.textFieldUser.text()

        # Captura del ID de usuario actual en BD
        view.id_usuario = db.execute("SELECT id FROM users WHERE nombre = ?", [usuario]).fetchone()

        # Captura de la Cartera Actual (la primera de todas las del Usuario)
        view.currentCartera = db.execute(
            "SELECT nombre_cartera FROM carteras WHERE id_usuario = ? ORDER BY (nombre_cartera)",
            ([view.id_usuario[0]])).fetchone()

        # Estructura de almacenamiento para los fondos seleccionados para graficar
        view.isins_selected = []

        # Conexión de los eventos de botones clickados a la lógica de los controladores
        view.buttonLogout.clicked.connect(view.logout)
        view.buttonAddISIN.clicked.connect(view.showAddIsin)
        view.buttonAddCarteras.clicked.connect(view.showAddCarteras)
        view.buttonBorrarCartera.clicked.connect(view.borrarCartera)
        view.buttonBorrarFondo.clicked.connect(view.borrarFondo)
        view.listIsins.itemClicked.connect(view.addIsinsChecked)

        view.H = Highstock()
        # Desactivación de los botones de borrar Cartera y Añadir Nuevo Fondo
        view.buttonBorrarCartera.setEnabled(False)
        view.buttonAddISIN.setEnabled(False)

        # Instancia del Widget WebEngine para la creación de Gráficos
        view.browser = QtWebEngineWidgets.QWebEngineView(view)

        # Carga del Combobox de selección de modo de graficación
        view.cbModo.addItems(['Absoluto', 'Evolución'])

        # Carga de la etiqueta con el Nombre de usuario actual
        view.labelUsuario.setText(usuario)

        # Carga de la etiqueta con el e-mail de usuario actual
        email = db.execute("SELECT email FROM users WHERE nombre = ?", [usuario]).fetchone()
        view.labelEmail.setText(email[0])

        # Carga de todas las Carteras Virtuales de las que dispone el Usuario
        view.carteras_usuario = db.execute(
            "SELECT num_cartera , nombre_cartera FROM carteras WHERE id_usuario = ? ORDER BY (nombre_cartera)",
            ([view.id_usuario[0]])).fetchall()

        # Nombres de cada cartera
        view.nombres_carteras = []
        for e in view.carteras_usuario:
            view.nombres_carteras.append(e[1])

        if len(view.nombres_carteras) > 0:
            view.labelCartera.setText('Fondos en ' + view.nombres_carteras[0])
        else:
            view.labelCartera.setText('No existen Carteras')
        #Adición de las Carteras al ComboBox de Selección de Carteras
        view.cbCarteras.addItems(view.nombres_carteras)

        # Activación del botón añadir Fondo si hay alguna cartera
        if view.cbCarteras.count() > 0:
            view.buttonAddISIN.setEnabled(True)

        # Si hay una cartera actual (si existen carteras) para el usuario actual
        if view.currentCartera is not None:

            # Carga todos los ISIN/Symbol de los fondos para la cartera actual
            ISINS = db.execute(
                "SELECT cu.ISIN FROM carteras c INNER JOIN carteras_usuario cu "
                "USING (nombre_cartera)"
                "WHERE c.nombre_cartera = ? AND cu.id_usuario = ? ",
                ([view.currentCartera[0], view.id_usuario[0]])).fetchall()
            isin_list = []
            for ISIN in ISINS:
                isin_list.append(ISIN[0])

            # Carga los nombres de los fondos en cartera añadiendo su ISIN/Symbol al final
            isin_list_view = []
            for ISIN in ISINS:
                isin_list_view.append(str(fundUtils.ISINtoFund(ISIN[0])) + "  (" + ISIN[0] + ")")

            # Carga el Widget de Selección de Fondos para graficar con los nombres de los Fondos en cartera
            for x in isin_list_view:
                item = QListWidgetItem(str(x))
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable | ~QtCore.Qt.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.Unchecked)
                view.listIsins.addItem(item)

            # Comprueba si existe el Fondo en BD y lo descarga en caso negativo
            for e in isin_list:
                fundUtils.saveHistoricalFund(view, e)

            # Actualiza el gráfico con los Fondos seleccionados
            fundUtils.graphHistoricalISIN(view, view.isins_selected, False)

        # Activa el botón de borrar Carteras si hay alguna Cartera
        if len(view.nombres_carteras) > 0:
            view.buttonBorrarCartera.setEnabled(True)

        # Conexión de las señales de eventos en los selectores de Selección de Cartera y Modo de Graficación
        view.cbCarteras.currentIndexChanged.connect(view.updateQList)
        view.cbModo.currentIndexChanged.connect(
            lambda clicked, isins_selected=view.isins_selected: view.updateGraph(None, view.isins_selected))


    '''
        - Borra el fondo seleccionado del ComboBox de la vista
        y elimina el registro de usuario para la cartera actual. 
        
        @params: view (UserView) 
        @returns: None
    '''
    def borrarFondo(view):
        db_connection = sqlite3.connect('DemoData.db', isolation_level=None)
        db = db_connection.cursor()
        index = view.cbCarteras.currentIndex()
        cartera = str(view.cbCarteras.itemText(index))

        name = view.listIsins.item(view.listIsins.currentRow()).text()
        nameSize = len(name)
        ISIN = name[nameSize - 13: nameSize - 1]
        if ISIN[1] == '(':
            ISIN = ISIN[2:12]
        db.execute("DELETE FROM carteras_usuario WHERE id_usuario = ? AND nombre_cartera = ? AND ISIN = ?",
                   ([view.id_usuario[0], cartera, ISIN]))

        view.listIsins.takeItem(view.listIsins.currentRow())
        view.updateGraph(isin=None , isins_selected=[])

    '''
        - Borra la cartera seleccionada del ComboBox de la vista
        y elimina el registro de usuario para la cartera actual.

        @params: view (UserView)
        @returns: None
    '''
    def borrarCartera(view):

        index = view.cbCarteras.currentIndex()

        db_connection = sqlite3.connect('DemoData.db', isolation_level=None)
        db = db_connection.cursor()
        cartera = str(view.cbCarteras.itemText(index))

        db.execute("DELETE FROM carteras WHERE id_usuario = ? AND nombre_cartera = ?",
                   ([view.id_usuario[0], cartera]))
        db.execute("DELETE FROM carteras_usuario WHERE id_usuario = ? AND nombre_cartera = ?",
                   ([view.id_usuario[0], cartera]))

        view.cbCarteras.removeItem(view.cbCarteras.currentIndex())

        if view.cbCarteras.count() > 0:
            view.buttonBorrarCartera.setEnabled(True)
        else:
            view.buttonBorrarCartera.setEnabled(False)

    '''
        - Actualiza la lista de selector con los fondos de la cartera actual

         @params: view (UserView)
         @returns: None
    '''
    def updateQList(view):

        try:
            view.listIsins.clear()
            view.isins_selected = []
            view.labelCartera.setText('Fondos en ' + view.cbCarteras.currentText())
            db_connection = sqlite3.connect('DemoData.db', isolation_level=None)
            db = db_connection.cursor()
            ISINS = db.execute(
                "SELECT cu.ISIN FROM carteras c INNER JOIN carteras_usuario cu "
                "USING (nombre_cartera)"
                "WHERE c.nombre_cartera = ? AND cu.id_usuario = ?   ",
                ([str(view.cbCarteras.currentText()), view.id_usuario[0]])).fetchall()

            isin_list = []
            for ISIN in ISINS:
                isin_list.append(ISIN[0])

            isin_list_view = []
            for ISIN in ISINS:
                isin_list_view.append(str(fundUtils.ISINtoFund(ISIN[0])) + "  (" + ISIN[0] + ")")

            for x in isin_list_view:
                item = QListWidgetItem(str(x))
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                item.setCheckState(QtCore.Qt.Unchecked)
                view.listIsins.addItem(item)


            for e in isin_list:
                fundUtils.saveHistoricalFund(view, e)

            fundUtils.graphHistoricalISIN(view, view.isins_selected, True)

        except:
            # Avisa al Usuario de que el fondo está descargándose
            dlg = downloadingIsinDialog(view)
            dlg.exec()

    '''
        - Añade el Fondo seleccionado a la lista de graficación
        y lo inserta en el gráfico.

         @params: self (UserView)
         @returns: None
    '''
    def addIsinsChecked(self):
        print("Captada la pulsación")

        try:

            # Captura del ISIN del Fondo seleccionado en la vista
            name = self.listIsins.item(self.listIsins.currentRow()).text()
            nameSize = len(name)
            ISIN = name[nameSize - 13: nameSize - 1]

            # Comprueba si ISIN es el ISIN del fondo (si existe en investing.com)
            # lanzando RuntimeError en caso negativo
            fundUtils.ISINtoFund(ISIN)

            # Añade o elimina el fondo seleccionado a la lista de graficación
            if ISIN in self.isins_selected:
                self.isins_selected.remove(ISIN)
                self.listIsins.currentItem().setCheckState(False)
                self.updateGraph(None, self.isins_selected)

            else:
                self.isins_selected.append(ISIN)
                self.listIsins.currentItem().setCheckState(True)
                # Actualiza el gráfico
                self.updateGraph(ISIN, self.isins_selected)


        # Se ha capturado la excepción de la API de investing.com, se procede
        # a intentar lo mismo pero tomando ISIN como si fuese un Symbol
        except :

            # Captura del ISIN del Fondo seleccionado en la vista
            name = self.listIsins.item(self.listIsins.currentRow()).text()
            nameSize = len(name)
            ISIN = name[nameSize - 11: nameSize - 1]

            # Añade o elimina el fondo seleccionado a la lista de graficación
            if ISIN in self.isins_selected:
                self.isins_selected.remove(ISIN)
                self.listIsins.currentItem().setCheckState(False)
                self.updateGraph(None, self.isins_selected)
            else:
                self.isins_selected.append(ISIN)
                self.listIsins.currentItem().setCheckState(True)
                # Actualiza el gráfico
                self.updateGraph(ISIN, self.isins_selected)


        print('FONDOS EN GRÁFICO: ')
        print(self.isins_selected)


    '''
        - Muestra la Interfaz Gráfica para Añadir Carteras

         @params: self (UserView)
         @returns: None
    '''
    def showAddCarteras(self):
        cart = AddCarterasView(self)
        cart.show()

    '''
        - Muestra la Interfaz Gráfica para Añadir Fondos

         @params: self (UserView)
         @returns: None
    '''
    def showAddIsin(self):
        merc = AddISINView(self)
        merc.show()

    '''
        - Sale de la ventana actual (UserView) y 
        muestra de nuevo la Interfaz Gráfica de LogIn (MainView)

         @params: self (UserView)
         @returns: None
    '''
    def logout(self):
        self.hide()
        self.parent().show()


    '''
        - Actualiza el gráfico del layout en UserView con la lista de 
        fondos seleccionados para graficar

         @params: self (UserView) 
                : lista de fondos seleccionados (isins_list)
         @returns: None
    '''
    def updateGraph(self, isin , isins_selected):
        if self.cbModo.currentIndex() == 0:
            fundUtils.UpdateGraph(self, isin , isins_selected, True)
        else:
            fundUtils.UpdateGraph(self, isin , isins_selected, False)