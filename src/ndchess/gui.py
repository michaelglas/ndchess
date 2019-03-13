'''
Created on 07.03.2019

@author: michi
'''
import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
import itertools
import ndchess
from ndchess import ina, hashable_array
from functools import reduce
from operator import xor
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import numpy
import cairo

square_size = 20
color_light = (1,1,1)
color_dark = (0,0,0)
selected_alpha = 0.5

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
    wc = numpy.empty(len(shape2d)+2,dtype=int)
    for i,sh in enumerate(shape2d,2):
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
        shape = self.chess.board.shape
        width = shape[0]
        height = shape[1]
        self.shape_2d = [width]
        if len(shape)>3:
            height = shape[1]
            self.shape_2d.append(height)
            for sh in self.chess.board.shape[2:-2]:
                if x:
                    width = width*sh
                    self.shape_2d.append(width)
                    x = False
                else:
                    height = height*sh
                    self.shape_2d.append(height)
                    x = True
        self.active_player = 1
        self.players = players
        self.selected = []
        self.selected_piece = None
        for i in self.chess.allowed_pieces[1:]:
            i.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(i.image,square_size,square_size,False)
        self.connect("button-press-event",self.button_pressed)
    def do_draw(self,cr):
        for wc in itertools.product(*map(range,self.chess.board.shape)):
            if reduce(xor,map(lambda x:bool(x%2),wc)):
                cr.set_source_rgb(*color_light)
            else:
                cr.set_source_rgb(*color_dark)
            sc = world_to_screen(wc, self.shape_2d)
            cr.rectangle(*sc,square_size,square_size)
            cr.fill()
            cont = self.chess.board[wc]
            if cont:
                Gdk.cairo_set_source_pixbuf(cr,self.chess.allowed_pieces[cont["piece"]].pixbuf,0,0)
                cr.get_source().set_matrix(cairo.Matrix(x0=-sc[0],y0=-sc[1]))
                cr.rectangle(*sc,square_size,square_size)
                cr.fill()
        if self.selected_piece:
            Gdk.cairo_set_source_pixbuf(cr,self.selected_piece.pixbuf,0,0)
            cr.get_source().set_extend(cairo.EXTEND_REPEAT)
        else:
            cr.set_source_rgb(1,0,0)
        for wc in self.selected:
            cr.rectangle(*world_to_screen(wc, self.shape_2d),square_size,square_size)
        cr.clip()
        cr.paint_with_alpha(selected_alpha)
        cr.reset_clip()
    
    def button_pressed(self,target,event):
        wc = screen_to_world((event.x,event.y), self.shape_2d)
        if self.selected:
            if numpy.array_equal(wc,self.selected[0]):
                self.selected = []
            elif ina(self.selected,wc):
                pos = tuple(self.selected[0])
                twc = tuple(wc)
                self.chess.board[twc] = self.chess.board[pos]
                self.chess.board[pos] = b""
                if self.chess.board[twc]["piece"]==1:
                    self.chess.king_positions.discard(self.selected[0].view(hashable_array))
                    self.chess.king_positions.add(wc.view(hashable_array))
                print(self.active_player)
                self.active_player = (self.active_player%self.players)+1
                print(self.active_player)
                self.selected = []
                self.selected_piece = None
        else:
            cont = self.chess.board[tuple(wc)]
            print(self.active_player)
            if cont["piece"] and cont["player"]==self.active_player:
                self.selected.append(wc)
                piece = self.chess.allowed_pieces[cont["piece"]]
                self.selected_piece = piece
                for i in piece.directions:
                    j = 1
                    while j<=piece.max_moves:
                        pos = wc+i*j
                        if (pos<0).any():
                            break
                        try:
                            cont2 = self.chess.board[tuple(pos)]
                        except IndexError:
                            break
                        if cont2["player"]==self.active_player:
                            break
                        self.selected.append(pos)
                        if cont2["piece"]:
                            break
                        j+=1
        self.queue_draw()

class widget(Gtk.EventBox):
    def __init__(self,chess):
        Gtk.EventBox.__init__(self)
        self.cwidget = lwidget(chess)
        self.add(self.cwidget)
        self.connect("button-press-event",self.cwidget.button_pressed)
    

class window(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.cwidget = widget(ndchess.ndChess((7,7,2,2),[ndchess.piece([numpy.array([1])], float("inf"),image="image.png")]*2))
        self.cwidget.cwidget.chess.place_piece((0,0,0,0),2,2)
        self.cwidget.cwidget.chess.place_piece((0,1,0,0),1,2)
        self.cwidget.cwidget.chess.place_piece((1,2,0,0),1,1)
        self.add(self.cwidget)

if __name__=="__main__":
    win = window()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
