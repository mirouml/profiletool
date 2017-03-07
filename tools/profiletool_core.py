# -*- coding: utf-8 -*-
#-----------------------------------------------------------
#
# Profile
# Copyright (C) 2008  Borys Jurgiel
# Copyright (C) 2012  Patrice Verchere
#-----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, print to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#---------------------------------------------------------------------

from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.Qt import *
from qgis.PyQt.QtSvg import * # required in some distros

from qgis.core import *
from qgis.gui import *

import platform
import sys
from math import sqrt
import numpy as np

from .dataReaderTool import DataReaderTool
from .plottingtool import PlottingTool
from .ptmaptool import ProfiletoolMapTool, ProfiletoolMapToolRenderer
from ..ui.ptdockwidget import PTDockWidget



class ProfileToolCore(QWidget):

    def __init__(self, iface,plugincore, parent = None):
        QWidget.__init__(self, parent)
        self.iface = iface
        self.plugincore = plugincore
        #the rubberband
        self.polygon = False
        self.rubberband = QgsRubberBand(self.iface.mapCanvas(), self.polygon)
        self.rubberband.setWidth(2)
        self.rubberband.setColor(QColor(Qt.red))
        self.rubberbandpoint = QgsVertexMarker(self.iface.mapCanvas())
        self.rubberbandpoint.setColor(QColor(Qt.red))
        self.rubberbandpoint.setIconSize(5)
        self.rubberbandpoint.setIconType(QgsVertexMarker.ICON_BOX) # or ICON_CROSS, ICON_X
        self.rubberbandpoint.setPenWidth(3)
        #mouse tracking
        self.doTracking = False
        #the dockwidget
        self.dockwidget = PTDockWidget(self.iface,self)     
        #dockwidget graph zone
        self.dockwidget.changePlotLibrary( self.dockwidget.cboLibrary.currentIndex() )
        #the datas / results
        self.profiles = None        #dictionary where is saved the plotting data {"l":[l],"z":[z], "layer":layer1, "curve":curve1}
        #The line information
        self.pointstoDraw = None
        #he renderer for temporary polyline
        self.toolrenderer = ProfiletoolMapToolRenderer(self)
        #the maptool previously loaded
        self.saveTool = self.iface.mapCanvas().mapTool()            #Save the standard mapttool for restoring it at the end
        
    def activateProfileMapTool(self):
        #Listeners of mouse
        self.toolrenderer.connectTool()
        #init the mouse listener comportement and save the classic to restore it on quit
        self.iface.mapCanvas().setMapTool(self.toolrenderer.tool)
        


    #******************************************************************************************
    #**************************** function part *************************************************
    #******************************************************************************************


    #def calculateProfil(self, points1, model1, library, vertline = True):
    def calculateProfil(self, points1,  vertline = True):
        self.disableMouseCoordonates()
        self.pointstoDraw = points1
        
        self.prepar_points(self.pointstoDraw)   #for mouse tracking
        self.removeClosedLayers(self.dockwidget.mdl)
        if self.pointstoDraw == None:
            return
        
        PlottingTool().clearData(self.dockwidget, self.profiles, self.dockwidget.plotlibrary)
        
        self.profiles = []
        
        if vertline:                        #Plotting vertical lines at the node of polyline draw
            PlottingTool().drawVertLine(self.dockwidget, self.pointstoDraw, self.dockwidget.plotlibrary)

        #calculate profiles
        for i in range(0 , self.dockwidget.mdl.rowCount()):
            self.profiles.append( {"layer": self.dockwidget.mdl.item(i,4).data(Qt.EditRole) } )
            self.profiles[i]["band"] = self.dockwidget.mdl.item(i,3).data(Qt.EditRole)
            self.profiles[i] = DataReaderTool().dataReaderTool(self.iface, self.toolrenderer.tool, self.profiles[i], self.pointstoDraw, self.dockwidget.checkBox.isChecked())
        #plot profiles
        PlottingTool().attachCurves(self.dockwidget, self.profiles, self.dockwidget.mdl, self.dockwidget.plotlibrary)
        PlottingTool().reScalePlot(self.dockwidget, self.profiles, self.dockwidget.plotlibrary)
        #create tab with profile xy
        self.dockwidget.updateCoordinateTab()
        #Mouse tracking
        if self.doTracking :
            self.rubberbandpoint.show()
        self.enableMouseCoordonates(self.dockwidget.plotlibrary)
                

    
    
    # remove layers which were removed from QGIS
    def removeClosedLayers(self, model1):
        qgisLayerNames = []
        for i in range(0, self.iface.mapCanvas().layerCount()):
                qgisLayerNames.append(self.iface.mapCanvas().layer(i).name())
        for i in range(0 , model1.rowCount()):
            layerName = model1.item(i,2).data(Qt.EditRole)
            if not layerName in qgisLayerNames:
                self.dockwidget.removeLayer(i)
                self.removeClosedLayers(model1)
                break
    

    def getProfileCurve(self,nr):
        try:
            return self.profiles[nr]["curve"]
        except:
            return None
            
    
    #******************************************************************************************
    #**************************** mouse interaction *******************************************
    #******************************************************************************************
            
    def activateMouseTracking(self,int1):

        if self.dockwidget.TYPE == 'PyQtGraph':
            
            if int1 == 2 :
                self.doTracking = True
                self.rubberbandpoint.show()
            elif int1 == 0 :
                self.doTracking = False
                self.rubberbandpoint.hide()
    
        elif self.dockwidget.TYPE == 'Matplotlib':
            if int1 == 2 :
                self.doTracking = True
                self.cid = self.dockwidget.plotWdg.mpl_connect('motion_notify_event', self.mouseevent_mpl)
            elif int1 == 0 :
                self.doTracking = False
                self.dockwidget.plotWdg.mpl_disconnect(self.cid)
                self.rubberbandpoint.hide()
                try:
                    if self.vline:
                        self.dockwidget.plotWdg.figure.get_axes()[0].lines.remove(self.vline)
                        self.dockwidget.plotWdg.draw()
                except Exception as e:
                    print(str(e) )
                    
                    

    def mouseevent_mpl(self,event):
        """
        case matplotlib library
        """
        if event.xdata:
            try:
                if self.vline:
                    self.dockwidget.plotWdg.figure.get_axes()[0].lines.remove(self.vline)
            except Exception as e:
                pass
            xdata = float(event.xdata)
            self.vline = self.dockwidget.plotWdg.figure.get_axes()[0].axvline(xdata,linewidth=2, color = 'k')
            self.dockwidget.plotWdg.draw()
            i=1
            while  i < len(self.tabmouseevent) and xdata > self.tabmouseevent[i][0] :
                i=i+1
            i=i-1
            x = self.tabmouseevent[i][1] +(self.tabmouseevent[i+1][1] - self.tabmouseevent[i][1] )/ ( self.tabmouseevent[i+1][0] - self.tabmouseevent[i][0]  )  *   (xdata - self.tabmouseevent[i][0])
            y = self.tabmouseevent[i][2] +(self.tabmouseevent[i+1][2] - self.tabmouseevent[i][2] )/ ( self.tabmouseevent[i+1][0] - self.tabmouseevent[i][0]  )  *   (xdata - self.tabmouseevent[i][0])  
            self.rubberbandpoint.show() 
            point = QgsPoint( x,y )
            self.rubberbandpoint.setCenter(point)
            
            
    def enableMouseCoordonates(self,library):
        if library == "PyQtGraph":
            self.dockwidget.plotWdg.scene().sigMouseMoved.connect(self.mouseMovedPyQtGraph)
            self.dockwidget.plotWdg.getViewBox().autoRange( items=self.dockwidget.plotWdg.getPlotItem().listDataItems())
            self.dockwidget.plotWdg.getViewBox().sigRangeChanged.connect(self.dockwidget.plotRangechanged)
            
            
    def disableMouseCoordonates(self):
        try:
            self.dockwidget.plotWdg.scene().sigMouseMoved.disconnect(self.mouseMovedPyQtGraph)
        except:
            pass
            
        try:
            self.dockwidget.plotWdg.getViewBox().sigRangeChanged.disconnect(self.dockwidget.plotRangechanged)
        except:
            pass
    
        
    def mouseMovedPyQtGraph(self, pos): # si connexion directe du signal "mouseMoved" : la fonction reçoit le point courant
            roundvalue = 3

            if self.dockwidget.plotWdg.sceneBoundingRect().contains(pos): # si le point est dans la zone courante
            
                if self.dockwidget.showcursor :
                    range = self.dockwidget.plotWdg.getViewBox().viewRange()
                    mousePoint = self.dockwidget.plotWdg.getViewBox().mapSceneToView(pos) # récupère le point souris à partir ViewBox
                    
                    datas = []
                    pitems = self.dockwidget.plotWdg.getPlotItem()
                    ytoplot = None
                    
                    if len(pitems.listDataItems())>0:
                        #get data and nearest xy from cursor
                        for i, item in enumerate(pitems.listDataItems()):
                            x,y = item.getData()
                            nearestindex = np.argmin( abs(np.array(np.array(x))-mousePoint.x()) )
                            xtoplot = np.array(x)[nearestindex]
                            if i == 0:
                                ytoplot = np.array(y)[nearestindex]
                            else:
                                if abs( np.array(y)[nearestindex] - mousePoint.y() ) < abs( ytoplot -  mousePoint.y() ):
                                    ytoplot = np.array(y)[nearestindex]
                                    
                        #plot xy label and cursor
                        for item in self.dockwidget.plotWdg.allChildItems():
                            if str(type(item)) == "<class 'profiletool.pyqtgraph.graphicsItems.InfiniteLine.InfiniteLine'>":
                                if item.name() == 'cross_vertical':
                                    item.show()
                                    item.setPos(xtoplot)
                                elif item.name() == 'cross_horizontal':
                                    item.show()
                                    item.setPos(ytoplot)
                            elif str(type(item)) == "<class 'profiletool.pyqtgraph.graphicsItems.TextItem.TextItem'>":
                                if item.textItem.toPlainText()[0] == 'X':
                                    item.show()
                                    item.setText('X : '+str(round(xtoplot,roundvalue)))
                                    item.setPos(xtoplot,range[1][0] )
                                elif item.textItem.toPlainText()[0] == 'Y':
                                    item.show()
                                    item.setText('Y : '+str(round(ytoplot,roundvalue)))
                                    item.setPos(range[0][0],ytoplot )
                                    

                                    
                                    
                    #tracking part
                    if self.doTracking:
                        i=1
                        while  i < len(self.tabmouseevent) and xtoplot > self.tabmouseevent[i][0] and xtoplot < self.tabmouseevent[-1][0] :
                            i=i+1
                        i=i-1
                        x = self.tabmouseevent[i][1] +(self.tabmouseevent[i+1][1] - self.tabmouseevent[i][1] )/ ( self.tabmouseevent[i+1][0] - self.tabmouseevent[i][0]  )  *   (xtoplot - self.tabmouseevent[i][0])
                        y = self.tabmouseevent[i][2] +(self.tabmouseevent[i+1][2] - self.tabmouseevent[i][2] )/ ( self.tabmouseevent[i+1][0] - self.tabmouseevent[i][0]  )  *   (xtoplot - self.tabmouseevent[i][0]) 
                        self.rubberbandpoint.show() 
                        
                        point = QgsPoint( x,y    )
                        self.rubberbandpoint.setCenter(point)


            
    def prepar_points(self,points1):
        self.tabmouseevent=[]
        len = 0
        for i,point in enumerate(points1):
            if i==0:
                self.tabmouseevent.append([0,point[0],point[1]])
            else:
                len = len + ( (points1[i][0] - points1[i-1][0] )**2 + (points1[i][1] - points1[i-1][1])**2 )**(0.5)
                if len ==0:
                    continue
                self.tabmouseevent.append([float(len) ,float(point[0]),float(point[1])])
        self.tabmouseevent = self.tabmouseevent[:-1]