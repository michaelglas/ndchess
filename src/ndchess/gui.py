#!/usr/bin/python3
'''
Created on 07.03.2019

@author: michi
'''
import sys
import os.path
sys.path.append(os.path.normpath(os.path.join(__file__,"../..")))

import gi
from os.path import abspath
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
import itertools
import ndchess
from ndchess import ina, hashable_array, flags, fileabspath, shellabspath
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import numpy
import cairo

square_size = 20
color_light = (1,1,1)
color_dark = (0,0,0)
selected_color = (1,0,0,0.5)
rect_color = [(0.745,0.207,0.035),(0.368,0.690,0.031),(0.564,0.129,0.690)]

def draw_checkerboard(cr,l,h):
    for x,y in itertools.product(range(l),range(h)):
        if x%2^y%2:
            cr.set_source_rgb(*color_light)
        else:
            cr.set_source_rgb(*color_dark)
        x *= square_size
        y *= square_size
        cr.rectangle(x,y,square_size,square_size)
        cr.fill()

def getd(l,i,d):
    return next(iter(l[i:]),d)

def world_to_screen(wc,shape2d):
    sx = wc[0]
    sy = wc[1]
    x = True
    for i,sh in zip(wc[2:],shape2d):
        if x:
            sx += sh*i
            x = False
        else:
            sy += sh*i
            x = True
    return square_size*sx,square_size*sy

def screen_to_world(sc,shape2d):
    x = sc[0]//square_size
    y = sc[1]//square_size
    ux = True
    wc = numpy.empty(len(shape2d),dtype=int)
    for i,sh in enumerate(shape2d[:-2],2):
        if ux:
            wc[i] = x//sh
            x = x%sh
            ux = False
        else:
            wc[i] = y//sh
            y = y%sh
            ux = True
    wc[0] = x
    wc[1] = y
    return wc

class lwidget(Gtk.Misc):
    def __init__(self,chess,players=2):
        Gtk.Misc.__init__(self)
        self.chess = chess
        self.shape_2d = []
        x = True
        self.shape = self.chess.board.shape
        width = self.shape[0]
        height = self.shape[1]
        self.shape_2d = [width]
        self.shape_2d.append(height)
        for sh in self.shape[2:]:#-2]:
            if x:
                width = width*sh
                self.shape_2d.append(width)
                x = False
            else:
                height = height*sh
                self.shape_2d.append(height)
                x = True
        self.width = width
        self.height = height
        self.active_player = 1
        self.players = players
        self.selected = []
        self.selected_piece = None
        self.selected_pos = None
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,self.width*square_size,self.height*square_size)
        self.tcr = cairo.Context(self.surface)
        self.piece = 1
        self.pieces = len(self.chess.allowed_pieces)-1
        self.player = 1
        self.nonexistent = GdkPixbuf.Pixbuf.new_from_file_at_scale(fileabspath("../../../pieces/nonexistent.png"),square_size,square_size,False)
        self.ctrl=False
        self.shift=False
        for i in self.chess.allowed_pieces[1:]:
            i.pixbufs = [GdkPixbuf.Pixbuf.new_from_file_at_scale(image,square_size,square_size,False) for image in i.images[:self.players]]
    def do_draw(self,cr):
        tcr = self.tcr
        tcr.set_source_rgba(0.0, 0.0, 0.0, 0.0)
        tcr.set_operator(cairo.OPERATOR_CLEAR)
        tcr.paint()
        tcr.set_operator(cairo.OPERATOR_OVER)
        
        for wc in itertools.product(*map(range,self.chess.board.shape)):
            sc = world_to_screen(wc, self.shape_2d)
            cont = self.chess.board[wc]
            if cont:
                Gdk.cairo_set_source_pixbuf(tcr,getd(self.chess.allowed_pieces[cont["piece"]].pixbufs,cont["player"]-1,self.nonexistent),0,0)
                tcr.get_source().set_matrix(cairo.Matrix(x0=-sc[0],y0=-sc[1]))
                tcr.rectangle(*sc,square_size,square_size)
                tcr.fill()
        
        if self.selected_piece:
            Gdk.cairo_set_source_pixbuf(tcr,getd(self.selected_piece.pixbufs,self.active_player-1,self.nonexistent),0,0)
            tcr.get_source().set_extend(cairo.EXTEND_REPEAT)
        else:
            tcr.set_source_rgb(1,0,0)
        for wc in self.selected:
            tcr.rectangle(*world_to_screen(wc, self.shape_2d),square_size,square_size)
        tcr.clip()
        tcr.paint()
        tcr.set_operator(cairo.OPERATOR_ATOP)
        tcr.set_source_rgba(*selected_color)
        tcr.paint()
        tcr.reset_clip()
        draw_checkerboard(cr, self.width, self.height)
        cr.set_source(cairo.SurfacePattern(self.surface))
        cr.paint()
        x = self.width*square_size
        y = self.height*square_size
        Gdk.cairo_set_source_pixbuf(cr,getd(self.chess.allowed_pieces[self.piece].pixbufs,self.player-1,self.nonexistent),0,0)
        cr.get_source().set_matrix(cairo.Matrix(x0=-x,y0=-y))
        cr.rectangle(x,y,square_size,square_size)
        cr.fill()
        length = len(self.shape)
        for i in range(2,length):
            x,y = world_to_screen(tuple(map(lambda x:x-1,self.shape[:i]))+(0,)*(length-i),self.shape_2d)
            x += square_size
            y += square_size
            zer = (0,)*i
            cr.set_source_rgb(*rect_color[i-2])
            for wc in itertools.product(*map(range,self.shape[i:])):
                sc = world_to_screen(zer+wc, self.shape_2d)
                cr.rectangle(*sc,x,y)
            cr.stroke()
    
    def check_ctrl(self,target,event,m):
        keyval = event.get_keyval().keyval
        if keyval==Gdk.KEY_Control_L:
            self.ctrl = m
        elif keyval==Gdk.KEY_Shift_L:
            self.shift = m
    
    def key_pressed(self,target,event):
        key = event.get_keyval().keyval
        if key==Gdk.KEY_Up:
            self.piece = (self.piece%self.pieces)+1
            self.queue_draw()
        elif key==Gdk.KEY_Down:
            self.piece = ((self.piece-2)%self.pieces)+1
            self.queue_draw()
        elif key==Gdk.KEY_Left:
            self.player = ((self.player-2)%self.players)+1
            self.queue_draw()
        elif key==Gdk.KEY_Right:
            self.player = (self.player%self.players)+1
            self.queue_draw()
    
    def button_pressed(self,target,event):
        wc = screen_to_world((event.x,event.y), self.shape_2d)
        #if self.ctrl:
        #    self.chess.place_piece(wc,self.piece,self.player)
        if self.selected:
            if numpy.array_equal(wc,self.selected_pos):
                self.selected = []
                self.selected_piece = None
                self.selected_pos = None
            elif self.ctrl or ina(self.selected,wc):
                self.chess.move_piece_low(self.selected_pos,wc)
                self.active_player = (self.active_player%self.players)+1
                self.selected = []
                self.selected_piece = None
                self.selected_pos = None
        elif self.ctrl:
            if self.shift:
                self.chess.clear_pos(wc)
            else:
                self.chess.place_piece(wc,self.piece,self.player)
        else:
            it = self.chess.get_all_moves(wc,self.active_player)
            try:
                self.selected_piece = next(it)
                self.selected = list(it)
                self.selected_pos = wc
            except StopIteration:
                pass
        self.queue_draw()

class widget(Gtk.EventBox):
    def __init__(self,chess):
        Gtk.EventBox.__init__(self)
        self.cwidget = lwidget(chess)
        self.add(self.cwidget)
        #self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
        #self.add_events(Gdk.EventMask.KEY_RELEASE_MASK)
        self.set_can_focus(True)
        self.connect("button-press-event",self.cwidget.button_pressed)
        self.connect("key-press-event",self.cwidget.check_ctrl,True)
        self.connect("key-press-event",self.cwidget.key_pressed)
        self.connect("key-release-event",self.cwidget.check_ctrl,False)
    

class window(Gtk.Window):
    def __init__(self,shape=(7,7,2,2),pieces=ndchess.pieces_from_file(fileabspath("../../../pieces/default.json"))):
        Gtk.Window.__init__(self)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
        self.add_events(Gdk.EventMask.KEY_RELEASE_MASK)
        self.cwidget = widget(ndchess.ndChess(shape,pieces))
        #self.cwidget.cwidget.chess.place_piece((0,0,0,0),2,2)
        #self.cwidget.cwidget.chess.place_piece((0,1,0,0),1,2)
        #self.cwidget.cwidget.chess.place_piece((1,2,0,0),1,1)
        self.add(self.cwidget)

if __name__=="__main__":
    shape = ()
    pieces = None
    if len(sys.argv)>1:
        shape = []
        cont = True
        for i,a in enumerate(sys.argv[1:],1):
            try:
                shape.append(int(a))
            except ValueError:
                pass
        else:
            cont = False
        if cont:
            pieces = ndchess.pieces_from_file(shellabspath(sys[i]))
    if not pieces:
        pieces = ndchess.pieces_from_file(fileabspath("../../../pieces/default.json"))
    win = window(tuple(shape) or (7,7,2,2),pieces)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
