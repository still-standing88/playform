from PySide6.QtWidgets import QPushButton, QGraphicsOpacityEffect
from PySide6.QtCore import Signal, QPropertyAnimation, QEasingCurve, QRect, Qt, QParallelAnimationGroup
from PySide6.QtGui import QFont

class ToggleButton(QPushButton):
    actuated = Signal(bool)
    

    def __init__(self, text=None, parent=None):
        super().__init__(parent)
        
        self.activated = False
        
        self.setupAnimations()
        
        self.setupStyle()
        
        self.clicked.connect(self.onActuate)
        
        self.setCursor(Qt.PointingHandCursor)
        
        if text and text.strip():
            self.setText(text)
        
        self.updateAccessibility()
        self.updateStyle()
        
        self.setMinimumSize(100, 35)
        
    def setupAnimations(self):
        self.animationGroup = QParallelAnimationGroup(self)
        
        self.opacityEffect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacityEffect)
        
        self.opacityAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.opacityAnimation.setDuration(200)
        self.opacityAnimation.setEasingCurve(QEasingCurve.InOutQuad)
        
        self.sizeAnimation = QPropertyAnimation(self, b"minimumSize")
        self.sizeAnimation.setDuration(250)
        self.sizeAnimation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.animationGroup.addAnimation(self.opacityAnimation)
        self.animationGroup.addAnimation(self.sizeAnimation)
        
    def setupStyle(self):
        self.base_style = """
            QPushButton {
                background-color: transparent;
                border: 2px solid rgba(46, 204, 113, 0.6);
                border-radius: 8px;
                padding: 8px 16px;
                font-family: "Segoe UI", Roboto, sans-serif;
                font-size: 13px;
                font-weight: 500;
                color: #2c3e50;
                text-align: center;
                transition: all 0.3s ease;
            }
            
            QPushButton:hover {
                border-color: rgba(46, 204, 113, 0.8);
                background-color: rgba(46, 204, 113, 0.05);
                transform: translateY(-1px);
            }
            
            QPushButton:pressed {
                transform: translateY(0px);
            }
        """
        
        self.activated_style = """
            QPushButton {
                background-color: #2ecc71;
                border: 2px solid #27ae60;
                border-radius: 8px;
                padding: 8px 16px;
                font-family: "Segoe UI", Roboto, sans-serif;
                font-size: 13px;
                font-weight: 600;
                color: white;
                text-align: center;
                transition: all 0.3s ease;
            }
            
            QPushButton:hover {
                background-color: #27ae60;
                border-color: #229954;
                transform: translateY(-1px);
                box-shadow: 0 4px 8px rgba(46, 204, 113, 0.3);
            }
            
            QPushButton:pressed {
                background-color: #229954;
                transform: translateY(0px);
            }
        """
        
    def updateStyle(self):
        if self.activated:
            self.setStyleSheet(self.activated_style)
            self.setProperty("toggled", True)
        else:
            self.setStyleSheet(self.base_style)
            self.setProperty("toggled", False)
        
        self.style().unpolish(self)
        self.style().polish(self)
        
    def updateAccessibility(self):
        if self.activated:
            self.setAccessibleDescription("Toggle button activated - Press to deactivate")
            self.setAccessibleName(f"{self.text()} - Active")
        else:
            self.setAccessibleDescription("Toggle button not activated - Press to activate")
            self.setAccessibleName(f"{self.text()} - Inactive")
            
    def setActuated(self, state):
        if isinstance(state, bool) and state != self.activated:
            self.activated = state
            self.actuatedChange()
            self.updateStyle()
            self.updateAccessibility()
            self.actuated.emit(self.activated)
        elif not isinstance(state, bool):
            raise TypeError("State must be boolean")
            
    def isActuated(self):
        return self.activated
        
    def onActuate(self):
        self.activated = not self.activated
        self.actuatedChange()
        self.updateStyle()
        self.updateAccessibility()
        self.actuated.emit(self.activated)
        
    def actuatedChange(self):
        if self.animationGroup.state() == QParallelAnimationGroup.Running:
            self.animationGroup.stop()
            
        self.opacityAnimation.setStartValue(1.0)
        self.opacityAnimation.setKeyValueAt(0.5, 0.7)
        self.opacityAnimation.setEndValue(1.0)
        
        current_size = self.minimumSize()
        
        if self.activated:
            target_size = self.size() if self.size().isValid() else current_size
            target_size.setWidth(max(target_size.width(), current_size.width() + 10))
            target_size.setHeight(max(target_size.height(), current_size.height() + 2))
        else:
            target_size = current_size
            
        self.sizeAnimation.setStartValue(current_size)
        self.sizeAnimation.setEndValue(target_size)
        
        self.animationGroup.start()
        
    def enterEvent(self, event):
        super().enterEvent(event)
        if hasattr(self, 'opacityEffect'):
            pass
            
    def leaveEvent(self, event):
        super().leaveEvent(event)
        if hasattr(self, 'opacityEffect'):
            pass
            
    def sizeHint(self):
        hint = super().sizeHint()
        hint.setWidth(max(hint.width(), 100))
        hint.setHeight(max(hint.height(), 35))
        return hint
        
    def setText(self, text):
        super().setText(text)
        self.updateAccessibility()
        
    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        if not enabled and hasattr(self, 'animationGroup'):
            self.animationGroup.stop()
            
    def __del__(self):
        if hasattr(self, 'animationGroup'):
            self.animationGroup.stop()