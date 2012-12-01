from PyQt4.QtGui import *
from PyQt4.QtCore import *

import json
import tempfile
import os
import dbus
import uuid
import math

class node(QGraphicsRectItem):
	DEAD = 1
	ALIVE = 2
	ACTIVATED = 3
	
	def __init__(self, the_uuid):
		QGraphicsRectItem.__init__(self)
		
		if None == the_uuid:
			self.uuid = uuid.uuid4().hex
		else:
			self.uuid = the_uuid
			
		self.monospace_font = QFont("monospace")
		self.monospace_font_metric = QFontMetrics(self.monospace_font)
		
		print "node"
		
		self.state = node.DEAD
		self.base_brush_color = [48*2, 85*2, 67*2]
		self.highlighed_brush_colors = { node.DEAD: [128, 0, 0], node.ALIVE: [0, 60, 0], node.ACTIVATED: [30, 30, 30] }
		self.highlight_timer_count = 0
		
		self.setRect(0,0,100,100)
		self.name = "node"

		self.setBrush(QBrush(QColor(48*2, 85*2, 67*2)))
		pen = QPen(QColor(48*3, 85*3, 67*3))
		pen.setWidth(4)
		self.setPen(pen)
		
		self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
		
		self.glow_timer = QTimer()
		self.glow_timer.setSingleShot(False)
		self.glow_timer.timeout.connect(self.glow_timer_timedout)
		self.glow_timer.setInterval(250)
		self.glow_timer.start()
	
	def color(self, array):
		capped = map(lambda x: min(255,x), array)
		return QColor(capped[0], capped[1], capped[2])
		
	def glow_timer_timedout(self):
		# print self.highlight_timer_count
		self.highlight_timer_count += 1
		self.highlight_timer_count %= 10
		if self.highlight_timer_count % 10 == 0:
			self.setBrush(QBrush(self.color(map(sum, zip(self.highlighed_brush_colors[self.state], self.base_brush_color)))))
		if self.highlight_timer_count % 10 == 1:
			self.setBrush(QBrush(self.color(self.base_brush_color)))
	
	def itemChange(self, change, value):
		# print "change"
		if change == QGraphicsItem.ItemPositionChange and not self.scene() == None:
			new_pos = value.toPointF()
			new_pos.setX(math.floor(new_pos.x() / self.monospace_font_metric.lineSpacing()) * (self.monospace_font_metric.lineSpacing()))
			new_pos.setY(math.floor(new_pos.y() / self.monospace_font_metric.lineSpacing()) * (self.monospace_font_metric.lineSpacing()))
			# print "pos"
			return new_pos
			
		return QGraphicsItem.itemChange(self, change, value)

class process_node(node):
	def __init__(self, the_uuid):
		node.__init__(self, the_uuid)

		self.process = QProcess()
		self.process.readyReadStandardOutput.connect(self.process_ready_read_stdout)
		self.process.readyReadStandardError.connect(self.process_ready_read_stderr)
		self.process.error.connect(self.process_error)
		self.process.finished.connect(self.process_finished)

	def make_service_name(self, service_name):
		return service_name + self.uuid
		
	def start(self):
		pass
	
	def stop(self):
		pass

	def process_error(self):
		self.state = node.DEAD
		
	def process_finished(self):
		self.state = node.DEAD
	
	def process_ready_read_stdout(self):
		print ("stdout", self.process.readAllStandardOutput())

	def process_ready_read_stderr(self):
		print ("stdout", self.process.readAllStandardError())

	def stop(self):
		print ("Stopping process:", self.library, self.label)

		if self.process.state() == QProcess.Running:
			print "kill process"
			os.kill(self.process.pid(), 2)
			
			print "wait until finished"
			self.process.waitForFinished()

			print("stdout", self.process.readAllStandardOutput())
			print("stderr", self.process.readAllStandardError())


class jack_client_node(process_node):
	def __init__(self, the_uuid):
		process_node.__init__(self, the_uuid)
		self.jack_client_ports = []

class connection(QGraphicsLineItem):
	def __init__(self, source, source_port_index, sink, sink_port_index):
		QGraphicsLineItem.__init__(self)
		

class ladspa_node(jack_client_node):
	def to_json(self):
		return {'__class__': 'ladspa_node', '__value__': { 'library': str(self.library), 'label': str(self.label), 'x': self.x(), 'y': self.y(), 'uuid': self.uuid } }

	def __init__(self, library, label, the_uuid = None):
		jack_client_node.__init__(self, the_uuid)

		print type(self)
		self.library = library
		self.label = label
		
		self.jack_name = QGraphicsTextItem()
		self.jack_name.setParentItem(self)
		
		self.plugin_name = QGraphicsTextItem()
		self.plugin_name.setParentItem(self)
		self.plugin_name.setPlainText(self.library + "\n" + self.label)
		
		self.ports = []
		self.sink_ports = []
		self.source_ports = []
		self.port_infos = []

		self.adjust_children()

		self.service_name = self.make_service_name("io.fps.doob.Ladspa" + str(self.label))

		try:
			self.bus = dbus.SessionBus()
			self.bus.add_signal_receiver(handler_function=self.process_port_changed, signal_name="PortsChanged", bus_name=self.service_name, dbus_interface="io.fps.doob.ladspa")
			self.bus.add_signal_receiver(handler_function=self.process_jack_client_name_changed, signal_name="JackNameChanged", bus_name=self.service_name, dbus_interface="io.fps.doob.jack_client")
			self.bus.add_signal_receiver(handler_function=self.process_plugin_name_changed, signal_name="PluginNameChanged", bus_name=self.service_name, dbus_interface="io.fps.doob.ladspa")
		except:
			print "GNAHAHAH"
			
		self.start()

	def is_port_control(self, arg):
		return arg & 0x8
	
	def is_port_input(self, arg):
		return arg & 0x1
	
	def process_jack_client_name_changed(self, arg):
		print ("jack_client name: ", arg)
		#self.jack_name.setPlainText(str(arg))
		self.adjust_children()
		pass

	def process_plugin_name_changed(self, arg):
		print ("plugin name: ", arg)
		self.plugin_name.setPlainText(str(arg))
		self.adjust_children()
		pass

	def adjust_children(self):
		# Remove all ports if they exist previously
		for port in self.ports:
			port.scene().removeItem(port)
		
		self.ports = []
		self.source_ports = []
		self.sink_ports = []

		#self.jack_name.adjustSize()
		#self.plugin_name.adjustSize()
		self.plugin_name.setY(self.jack_name.boundingRect().height())
		plugin_name_rect = self.plugin_name.boundingRect()
		y_offset = plugin_name_rect.y() + plugin_name_rect.height()
		
		for port in self.port_infos:
			portname = QGraphicsTextItem()
			portname.setParentItem(self)
			portname.setPlainText(port[0])
			portname.adjustSize()

			name_background = QGraphicsRectItem()
			name_background.setParentItem(portname)
			name_background.setRect(portname.boundingRect())
			name_background.setPen(QPen(QColor(0,0,0,0)))
			if self.is_port_control(port[1]):
				name_background.setBrush(QBrush(QColor(0,0,255,20)))
			else:
				name_background.setBrush(QBrush(QColor(255,0,0,20)))

			self.ports.append(portname)
			if self.is_port_input(port[1]):
				self.sink_ports.append(portname)
			else:
				self.source_ports.append(portname)

			portname.setY(y_offset)
			
			y_offset += portname.boundingRect().height() + 4

		for port in self.source_ports:
			the_rect = port.boundingRect()
			the_bounding_rect = self.childrenBoundingRect()
			# print(the_bounding_rect.width() - the_rect.width())
			portname.setX(the_bounding_rect.width() - the_rect.width())

		the_bounding_rect = self.childrenBoundingRect()
		self.setRect(the_bounding_rect)


	def process_port_changed(self, arg):
		print ("######################### process ports changed", arg)
		self.state = node.ACTIVATED
		self.port_infos = arg

		self.adjust_children()
		

		
	def start(self):
		args = ["--library="+self.library, "--label="+self.label, "--service-name="+self.service_name]
		self.process.start("doob.ladspa", args)
		
		if False == self.process.waitForStarted():
			print ("Failed to start")
			return
		
		self.state = node.ALIVE
		


class midi_note_node(jack_client_node):
	def __init__(self):
		jack_client_node.__init__(self)


class graph_view(QGraphicsView):
	def to_json(self):
		t = self.transform()
		return {'__class__': 'graph_view', '__value__': [t.m11(), t.m12(), t.m13(), t.m21(), t.m22(), t.m23(), t.m31(), t.m32(), t.m33(), self.verticalScrollBar().value(), self.horizontalScrollBar().value(), self.zoom_factor_exponent ] } 
	
	
	def __init__(self):
		QGraphicsView.__init__(self)
		self.zoom_factor_exponent = 0
		self.zoom_factor_base = 1.1
		
	def overlay_timer_timeout(self):
		pass
	
	def wheelEvent(self, event):
		if event.modifiers() & Qt.ControlModifier:
			if event.delta() > 0:
				print "scroll plus"
				self.zoom_factor_exponent += 1
			else:
				print "scroll minus"
				self.zoom_factor_exponent -= 1
				
			transform = self.transform()
			transform.setMatrix(1, 0, 0, 0, 1, 0, transform.m31(), transform.m32(), 1)
			scale = self.zoom_factor_base ** self.zoom_factor_exponent
			transform.scale(scale, scale)
			self.setTransform(transform)
			
			event.accept()
		else:
			QGraphicsView.wheelEvent(self, event)

class navigation_view(QGraphicsView):
	def __init__(self, the_main_window):
		QGraphicsView.__init__(self, the_main_window)
		
		self.the_main_window = the_main_window

		# TODO: fix this hack by proper event handling
		timer = QTimer(self)
		timer.setInterval(500)
		timer.setSingleShot(False)
		timer.timeout.connect(self.adjust)
		timer.start()
		

	def adjust(self):
		self.invalidateScene(layers = QGraphicsScene.ForegroundLayer)
		self.viewport().update()
		#self.update()
		pass
	
	def resizeEvent(self, event):
		QGraphicsView.resizeEvent(self, event)
		self.fit()
	
	def showEvent(self, event):
		QGraphicsView.showEvent(self, event)
		self.fit()
	
	def fit(self):
		self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
		# print "FIT"
		
	def drawForeground(self, painter, rect):
		QGraphicsView.drawForeground(self, painter, rect)
		if not self.the_main_window.tab_widget.currentIndex() == -1:
			painter.setBrush(QColor(255, 255, 255, 40))
			painter.setPen(QColor(255, 255, 255, 80))
			view = self.the_main_window.tab_widget.currentWidget()
			#painter.fillRect(view.mapToScene(view.viewport().geometry()).boundingRect(), QBrush(QColor(1.0, 1.0, 1.0, 0.5)))
			painter.drawRect(view.mapToScene(view.viewport().geometry()).boundingRect())
	
	def mousePressEvent(self, event):
		QGraphicsView.mousePressEvent(self, event)
		if not self.the_main_window.tab_widget.currentIndex() == -1:
			view = self.the_main_window.tab_widget.currentWidget()
			
			view.centerOn(self.mapToScene(event.pos()))
		