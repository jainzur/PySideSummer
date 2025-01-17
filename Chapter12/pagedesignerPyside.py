# -*- coding: utf-8 -*-
"""
pagedesignerPyside.py
Annotated PySide port of pagedesigner.py from Chapter 12
of Mark Summerfield's 'Rapid GUI Programming with Python and Qt' (2008)
Book's web site: http://www.qtrac.eu/pyqtbook.html

Notes on translation: 
self.borders.append(self.scene.addRect(rect, QtCore.Qt.yellow))
Doesn't take qt.yellow as third input need to give it pen
pen=QtGui.QPen(QtCore.Qt.yellow, 4) 

Replace QMatrix with QTransform, and .matrix attribute with .transform
E.g., QGraphicsTextItem.matrix() --> .transform()


------            
This script is part of the PySideSummer repository at GitHub:
https://github.com/EricThomson/PySideSummer

Code is under the GPL license: http://www.gnu.org/copyleft/gpl.html
"""


import functools
import random
import sys
from PyQt5 import QtGui, QtCore,QtWidgets,QtPrintSupport
       
MAC = "qt_mac_set_native_menubar" in dir()

#PageSize = (595, 842) # A4 in points
PageSize = (612, 792) # US Letter in points
PointSize = 10

MagicNumber = 0x70616765
FileVersion = 1

Dirty = False #uses global to tell if it has been changed


class GraphicsView(QtWidgets.QGraphicsView):

    def __init__(self, parent=None):
        super(GraphicsView, self).__init__(parent)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setRenderHint(QtGui.QPainter.TextAntialiasing)


    def wheelEvent(self, event):
        factor = 1.41 ** (event.angleDelta().y() / 240.0)
        self.scale(factor, factor)


class MainForm(QtWidgets.QDialog):

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.filename = ""
        self.copiedItem = QtCore.QByteArray()
        self.pasteOffset = 5
        self.prevPoint = QtCore.QPoint()
        self.addOffset = 5
        self.borders = []

        self.printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.PrinterMode.HighResolution)
        self.printer.setPageSize(QtGui.QPageSize())

        self.view = GraphicsView()
        self.scene = QtWidgets.QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, PageSize[0], PageSize[1])
        self.addBorders()
        self.view.setScene(self.scene)

        buttonLayout = QtWidgets.QVBoxLayout()
        for text, slot in (
                ("Add &Text", self.addText),
                ("Add &Box", self.addBox),
                ("Add Pi&xmap", self.addPixmap),
                ("&Copy", self.copy),
                ("C&ut", self.cut),
                ("&Paste", self.paste),
                ("&Delete...", self.delete),
                ("&Rotate", self.rotate),
                ("Pri&nt...", self.print_),
                ("&Open...", self.open),
                ("&Save", self.save),
                ("&Quit", self.accept)):
            button = QtWidgets.QPushButton(text)
            if not MAC:
                button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            button.clicked.connect(slot) #self.connect(button, SIGNAL("clicked()"), slot)
            if text == "Pri&nt...":
                buttonLayout.addStretch(5)
            if text == "&Quit":
                buttonLayout.addStretch(1)
            buttonLayout.addWidget(button)
        buttonLayout.addStretch()

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.view, 1)
        layout.addLayout(buttonLayout)
        self.setLayout(layout)

        fm = QtGui.QFontMetrics(self.font())
        self.resize(int(self.scene.width() + fm.width(" Delete... ")+ 50),int(self.scene.height() + 50))
        self.setWindowTitle("Page Designer")


    def addBorders(self):
        self.borders = []
        rect = QtCore.QRectF(0, 0, PageSize[0], PageSize[1])
        #print "rect type and qtcore.qt.yellow type:\n ", type(rect), type(QtCore.Qt.yellow)
        pen=QtGui.QPen(QtCore.Qt.GlobalColor.black)
        self.borders.append(self.scene.addRect(rect, pen))
        margin = 5.25 * PointSize
        
        self.borders.append(self.scene.addRect(
                rect.adjusted(margin, margin, -margin, -margin),
                pen))

    def removeBorders(self):
        while self.borders:
            item = self.borders.pop()
            self.scene.removeItem(item)
            del item

        
    def reject(self):
        self.accept()


    def accept(self):
        self.offerSave()
        QtWidgets.QDialog.accept(self)


    def offerSave(self):
        #print "offerSave Dirty? {0}".format(Dirty)
        
        if (Dirty and QtWidgets.QMessageBox.question(self,
                            "Page Designer - Unsaved Changes",
                            "Save unsaved changes?",
                            QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No) ==
            QtWidgets.QMessageBox.Yes):
            self.save()


    def position(self):
        point = self.mapFromGlobal(QtGui.QCursor.pos())
        if not self.view.geometry().contains(point):
            coord = random.randint(36, 144)
            point = QtCore.QPoint(coord, coord)
        else:
            if point == self.prevPoint:
                point += QtCore.QPoint(self.addOffset, self.addOffset)
                self.addOffset += 5
            else:
                self.addOffset = 5
                self.prevPoint = point
        return self.view.mapToScene(point)


    def addText(self):
        dialog = TextItemDlg(position=self.position(),
                             scene=self.scene, parent=self)
        dialog.exec_()


    def addBox(self):
        BoxItem(self.position(), self.scene)


    def addPixmap(self):
        path = QtCore.QFileInfo(self.filename).path() if self.filename else "."
        fname = QtWidgets.QFileDialog.getOpenFileName(self,
                "Page Designer - Add Pixmap", path,
                "Pixmap Files (*.bmp *.jpg *.png *.xpm)")[0]
        if not fname:
            return
        self.createPixmapItem(QtGui.QPixmap(fname), self.position())


    def createPixmapItem(self, pixmap, position, transform=QtGui.QTransform()):
        #print "Painting pixmap"
        item = QtWidgets.QGraphicsPixmapItem(pixmap)
        item.setFlags(QtWidgets.QGraphicsItem.ItemIsSelectable|
                      QtWidgets.QGraphicsItem.ItemIsMovable)
        item.setPos(position)
        item.setTransform(transform)
        self.scene.clearSelection()
        self.scene.addItem(item)
        item.setSelected(True)
        global Dirty
        Dirty = True
        #print "Got dirty when creating pixmap"


    def selectedItem(self):
        items = self.scene.selectedItems()
        if len(items) == 1:
            return items[0]
        return None


    def copy(self):
        item = self.selectedItem()
        if item is None:
            return
        self.copiedItem.clear()
        self.pasteOffset = 5
        stream = QtCore.QDataStream(self.copiedItem, QtCore.QIODevice.WriteOnly)
        self.writeItemToStream(stream, item)


    def cut(self):
        item = self.selectedItem()
        if item is None:
            return
        self.copy()
        self.scene.removeItem(item)
        del item


    def paste(self):
        if self.copiedItem.isEmpty():
            return
        stream = QtCore.QDataStream(self.copiedItem, QtCore.QIODevice.ReadOnly)
        self.readItemFromStream(stream, self.pasteOffset)
        self.pasteOffset += 5


    def rotate(self):
        for item in self.scene.selectedItems():
            item.setRotation(item.rotation() + 30)



    def delete(self):
        items = self.scene.selectedItems()
        if (len(items) and QtWidgets.QMessageBox.question(self,
                "Page Designer - Delete",
                "Delete {} item{}?".format(len(items),
                "s" if len(items) != 1 else ""),
                QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No) ==
                QtWidgets.QMessageBox.Yes):
            while items:
                item = items.pop()
                self.scene.removeItem(item)
                del item
            global Dirty
            Dirty = True
            #print "Got dirty deleting an item"


    def print_(self):
        dialog = QtPrintSupport.QPrintDialog(self.printer)
        if dialog.exec_():
            painter = QtGui.QPainter(self.printer)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setRenderHint(QtGui.QPainter.TextAntialiasing)
            self.scene.clearSelection()
            self.removeBorders()
            self.scene.render(painter)
            self.addBorders()


    def open(self):
        self.offerSave()
        path = QtCore.QFileInfo(self.filename).path() if self.filename else "."
        fname = QtWidgets.QFileDialog.getOpenFileName(self,
                "Page Designer - Open", path,
                "Page Designer Files (*.pgd)")[0]
        if not fname:
            return
        self.filename = fname
        fh = None
        try:
            fh = QtCore.QFile(self.filename)
            if not fh.open(QtCore.QIODevice.ReadOnly):
                raise IOError(fh.errorString())
            items = self.scene.items()
            while items:
                item = items.pop()
                self.scene.removeItem(item)
                del item
            self.addBorders()
            stream = QtCore.QDataStream(fh)
            stream.setVersion(QtCore.QDataStream.Qt_4_2)
            magic = stream.readInt32()
            if magic != MagicNumber:
                raise IOError("not a valid .pgd file")
            fileVersion = stream.readInt16()
            if fileVersion != FileVersion:
                raise IOError("unrecognised .pgd file version")
            while not fh.atEnd():
                self.readItemFromStream(stream)
        except IOError as e:
            QtGui.QMessageBox.warning(self, "Page Designer -- Open Error",
                    "Failed to open {}: {}".format(self.filename, e))
        finally:
            if fh is not None:
                fh.close()
        global Dirty
        Dirty = False
        #print "Just ran open: file should now be clean"


    def save(self):
        if not self.filename:
            path = "."
            fname = QtWidgets.QFileDialog.getSaveFileName(self,
                    "Page Designer - Save As", path,
                    "Page Designer Files (*.pgd)")[0]
            #print "save: fname, type: \n", fname, ",", type(fname)
            if not fname:
                return
            if not fname.lower().endswith(".pgd"):
                fname += ".pgd"
            self.filename = fname
        fh = None
        try:
            fh = QtCore.QFile(self.filename)
            if not fh.open(QtCore.QIODevice.WriteOnly):
                raise IOError(fh.errorString())
            self.scene.clearSelection()
            stream = QtCore.QDataStream(fh)
            stream.setVersion(QtCore.QDataStream.Qt_4_2)
            stream.writeInt32(MagicNumber)
            stream.writeInt16(FileVersion)
            for item in self.scene.items():
                self.writeItemToStream(stream, item)
        except IOError as e:
            QtGui.QMessageBox.warning(self, "Page Designer -- Save Error",
                    "Failed to save {}: {}".format(self.filename, e))
        finally:
            if fh is not None:
                fh.close()
        global Dirty
        Dirty = False


    def readItemFromStream(self, stream, offset=0):
        type = ""
        position = QtCore.QPointF()
        transform = QtGui.QTransform()
        type = stream.readQString()
        stream >> position >> transform
        if offset:
            position += QtCore.QPointF(offset, offset)
        if type == "Text":
            text = stream.readQString()
            font = QtGui.QFont()
            stream >> font
            TextItem(text, position, self.scene, font, transform)
        elif type == "Box":
            rect = QtCore.QRectF()
            stream >> rect
            style = QtCore.Qt.PenStyle(stream.readInt16())
            BoxItem(position, self.scene, rect,transform,style,)
        elif type == "Pixmap":
            pixmap = QtGui.QPixmap()
            stream >> pixmap
            self.createPixmapItem(pixmap, position, transform)  #this makes it dirty


    def writeItemToStream(self, stream, item):
        if isinstance(item, QtWidgets.QGraphicsTextItem):
            stream.writeQString("Text")
            stream << item.pos() << item.transform()
            stream.writeQString(item.toPlainText())
            stream << item.font()
        elif isinstance(item, QtWidgets.QGraphicsPixmapItem):
            stream.writeQString("Pixmap")
            stream << item.pos() << item.transform() << item.pixmap()
        elif isinstance(item, BoxItem):
            stream.writeQString("Box")
            stream << item.pos() << item.transform() << item.rect
            stream.writeInt16(item.style)
            
            
class TextItemDlg(QtWidgets.QDialog):

    def __init__(self, item=None, position=None, scene=None, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.item = item
        self.position = position
        self.scene = scene

        self.editor = QtWidgets.QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setTabChangesFocus(True)
        editorLabel = QtWidgets.QLabel("&Text:")
        editorLabel.setBuddy(self.editor)
        self.fontComboBox = QtWidgets.QFontComboBox()
        self.fontComboBox.setCurrentFont(QtGui.QFont("Times", PointSize))
        fontLabel = QtWidgets.QLabel("&Font:")
        fontLabel.setBuddy(self.fontComboBox)
        self.fontSpinBox = QtWidgets.QSpinBox()
        self.fontSpinBox.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.fontSpinBox.setRange(6, 280)
        self.fontSpinBox.setValue(PointSize)
        fontSizeLabel = QtWidgets.QLabel("&Size:")
        fontSizeLabel.setBuddy(self.fontSpinBox)
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|
                                          QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        if self.item is not None:
            self.editor.setPlainText(self.item.toPlainText())
            self.fontComboBox.setCurrentFont(self.item.font())
            self.fontSpinBox.setValue(self.item.font().pointSize())

        layout = QtWidgets.QGridLayout()
        layout.addWidget(editorLabel, 0, 0)
        layout.addWidget(self.editor, 1, 0, 1, 6)
        layout.addWidget(fontLabel, 2, 0)
        layout.addWidget(self.fontComboBox, 2, 1, 1, 2)
        layout.addWidget(fontSizeLabel, 2, 3)
        layout.addWidget(self.fontSpinBox, 2, 4, 1, 2)
        layout.addWidget(self.buttonBox, 3, 0, 1, 6)
        self.setLayout(layout)

        self.fontComboBox.currentFontChanged.connect(self.updateUi)
        self.fontSpinBox.valueChanged.connect(self.updateUi)
        self.editor.textChanged.connect(self.updateUi)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.setWindowTitle("Page Designer - {} Text Item".format(
                "Add" if self.item is None else "Edit"))
        self.updateUi()


    def updateUi(self):
        font = self.fontComboBox.currentFont()
        font.setPointSize(self.fontSpinBox.value())
        self.editor.document().setDefaultFont(font)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(
                bool(self.editor.toPlainText()))


    def accept(self):
        if self.item is None:
            self.item = TextItem("", self.position, self.scene)
        font = self.fontComboBox.currentFont()
        font.setPointSize(self.fontSpinBox.value())
        self.item.setFont(font)
        self.item.setPlainText(self.editor.toPlainText())   
        self.item.update()
        global Dirty
        Dirty = True
        #print "Got dirty when accepting textitemdlg"
        QtWidgets.QDialog.accept(self)


class TextItem(QtWidgets.QGraphicsTextItem):

    def __init__(self, text, position, scene,
                font=QtGui.QFont("Times", PointSize), transform=QtGui.QTransform()):
        QtWidgets.QGraphicsTextItem.__init__(self, text)
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsSelectable|
                      QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setFont(font)
        self.setPos(position)
        #print "TextItem transform: ", transform
        self.setTransform(transform)
        scene.clearSelection()
        scene.addItem(self)
        self.setSelected(True)
        global Dirty
        Dirty = True
        #print "Dirty in text item init"


    def parentWidget(self):
        return self.scene().views()[0]


    def itemChange(self, change, variant):
        if change != QtWidgets.QGraphicsItem.ItemSelectedChange:
            global Dirty
            Dirty = True
            #print "Got dirty in TextItem itemChange"
        return QtWidgets.QGraphicsTextItem.itemChange(self, change, variant)


    def mouseDoubleClickEvent(self, event):
        dialog = TextItemDlg(self, self.parentWidget())
        dialog.exec_()


class BoxItem(QtWidgets.QGraphicsItem):

    def __init__(self, position, scene,rect=None, transform=QtGui.QTransform(),style=QtCore.Qt.SolidLine):
        QtWidgets.QGraphicsItem.__init__(self)
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsSelectable|
                      QtWidgets.QGraphicsItem.ItemIsMovable|
                      QtWidgets.QGraphicsItem.ItemIsFocusable)
        if rect is None:
            rect = QtCore.QRectF(-10 * PointSize, -PointSize, 20 * PointSize,
                          2 * PointSize)
        self.rect = rect
        self.style = style
        self.setPos(position)
        #print "BoxItem transform: ", transform
        self.setTransform(transform)
        scene.clearSelection()
        scene.addItem(self)
        self.setSelected(True)
        self.setFocus()
        global Dirty
        Dirty = True
        #print "Got dirty in BoxItem init"

    #assumes box is in first in list of views (why?)
    def parentWidget(self):
        return self.scene().views()[0]


    def boundingRect(self):
        return self.rect.adjusted(-2, -2, 2, 2)

    #Paints the item
    def paint(self, painter, option, widget):
        pen = QtGui.QPen(self.style)
        pen.setColor(QtCore.Qt.black)
        pen.setWidth(1)
        if option.state & QtWidgets.QStyle.State_Selected:
            pen.setColor(QtCore.Qt.blue)
        painter.setPen(pen)
        painter.drawRect(self.rect)


    def itemChange(self, change, variant):
        if change != QtWidgets.QGraphicsItem.ItemSelectedChange:
            global Dirty
            Dirty = True
            #print "Got dirty in BoxItem itemChange"
        return QtWidgets.QGraphicsItem.itemChange(self, change, variant)  #this is seriously weird


    def contextMenuEvent(self, event):
        wrapped = []
        menu = QtWidgets.QMenu(self.parentWidget())
        for text, param in (
                ("&Solid", QtCore.Qt.SolidLine),
                ("&Dashed", QtCore.Qt.DashLine),
                ("D&otted", QtCore.Qt.DotLine),
                ("D&ashDotted", QtCore.Qt.DashDotLine),
                ("DashDo&tDotted", QtCore.Qt.DashDotDotLine)):
            wrapper = functools.partial(self.setStyle, param)
            wrapped.append(wrapper)
            menu.addAction(text, wrapper)
        menu.exec_(event.screenPos())


    def setStyle(self, style):
        self.style = style
        self.update()
        global Dirty
        Dirty = True
        #print "Got dirty in BoxItem set style"


    def keyPressEvent(self, event):
        factor = PointSize / 4
        changed = False
        if event.modifiers() & QtCore.Qt.ShiftModifier:
            if event.key() == QtCore.Qt.Key_Left:
                self.rect.setRight(self.rect.right() - factor)
                changed = True
            elif event.key() == QtCore.Qt.Key_Right:
                self.rect.setRight(self.rect.right() + factor)
                changed = True
            elif event.key() == QtCore.Qt.Key_Up:
                self.rect.setBottom(self.rect.bottom() - factor)
                changed = True
            elif event.key() == QtCore.Qt.Key_Down:
                self.rect.setBottom(self.rect.bottom() + factor)
                changed = True
        if changed:
            self.update()
            global Dirty
            Dirty = True
            #print "Got dirty when changing box w/key presses"
        else:
            QtWidgets.QGraphicsItem.keyPressEvent(self, event)


app = QtWidgets.QApplication(sys.argv)
form = MainForm()
rect = QtWidgets.QApplication.desktop().availableGeometry()
form.resize(int(rect.width() * 0.6), int(rect.height() * 0.9))
form.show()
app.exec_()

