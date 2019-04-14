#!/usr/bin/python3
'''
Created on 07.03.2019

@author: michi
'''
import sys
import os.path
import operator
sys.path.append(os.path.normpath(os.path.join(__file__,"../..")))

import gi
from os.path import abspath
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
import itertools
import ndchess
from ndchess import hashable_array, flags, fileabspath, shellabspath
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import numpy
import cairo
from math import ceil,floor

square_size = 20
color_light = (1.0, 0.807, 0.619)#(1,1,1)
color_dark = (0.819, 0.545, 0.278)#(0,0,0)
selected_color = (1,0,0,0.5)
rect_color = [(0.745,0.207,0.035),(0.368,0.690,0.031),(0.564,0.129,0.690),(0,0,0)]

get_end = operator.attrgetter("end")

class int_tuple(tuple):
    def __new__(cls,string):
        return tuple.__new__(cls,map(int,string.split(",")))

class pieces_file(list):
    def __init__(self,string):
        list.__init__(self,ndchess.pieces_from_file(fileabspath(string)))

def index_iter(iter,value):
    for i,v in enumerate(iter):
        if v==value:
            return i

def enumerate2(xs, start=0, step=1):
    for x in xs:
        yield (start, x)
        start += step

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

def sg(a):
    yield a

def get_all_ints_in_range(start,stop):
    return range(floor(start),ceil(stop))

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
    lsh = len(shape2d)
    ux = bool(lsh%2)
    wc = numpy.empty(lsh+2,dtype=int)
    for i,sh in enumerate2(reversed(shape2d), lsh+1, -1):
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
    return wc.view(hashable_array)

def sq_to_world(sc,shape2d):
    x = floor(sc[0])
    y = floor(sc[1])
    lsh = len(shape2d)
    ux = bool(lsh%2)
    wc = numpy.empty(lsh+2,dtype=int)
    for i,sh in enumerate2(reversed(shape2d), lsh+1, -1):
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
        self.shape = self.chess.shape
        self.calculate_shape2d()
        self.active_player = 0
        self.players = players
        self.selected_piece = None
        self.moves = []
        self.selected_pos = None
        self.flags = flags.MOVED
        self.bit = 0
        self.coords = None
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,self.width*square_size,self.height*square_size)
        self.tcr = cairo.Context(self.surface)
        self.piece = 1
        self.pieces = len(self.chess.allowed_pieces)-1
        self.player = 0
        self.nonexistent = GdkPixbuf.Pixbuf.new_from_file_at_scale(fileabspath("../../../pieces/nonexistent.png"),square_size,square_size,False)
        self.ctrl=False
        self.shift=False
        self.shape_pos = 1
        for i in self.chess.allowed_pieces[1:]:
            i.pixbufs = [GdkPixbuf.Pixbuf.new_from_file_at_scale(image,square_size,square_size,False) for image in i.images[:self.players]]
    def do_draw(self,cr):
        tcr = self.tcr
        tcr.set_source_rgba(0.0, 0.0, 0.0, 0.0)
        tcr.set_operator(cairo.OPERATOR_CLEAR)
        tcr.paint()
        tcr.set_operator(cairo.OPERATOR_OVER)
        
        for wc,cont in self.chess.board.items():
            if isinstance(cont, ndchess.field):
                sc = world_to_screen(wc, self.shape_2d)
                Gdk.cairo_set_source_pixbuf(tcr,getd(self.chess.allowed_pieces[cont.piece].pixbufs,cont.player,self.nonexistent),0,0)
                tcr.get_source().set_matrix(cairo.Matrix(x0=-sc[0],y0=-sc[1]))
                tcr.rectangle(*sc,square_size,square_size)
                tcr.fill()
        
        if self.selected_piece:
            Gdk.cairo_set_source_pixbuf(tcr,getd(self.selected_piece.pixbufs,self.active_player,self.nonexistent),0,0)
            tcr.get_source().set_extend(cairo.EXTEND_REPEAT)
        else:
            tcr.set_source_rgb(1,0,0)
        for wc in map(get_end,self.moves):
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
        if self.ctrl:
            Gdk.cairo_set_source_pixbuf(cr,getd(self.chess.allowed_pieces[self.piece].pixbufs,self.player,self.nonexistent),0,0)
            cr.get_source().set_matrix(cairo.Matrix(x0=-x,y0=-y))
            cr.rectangle(x,y,square_size,square_size)
            cr.fill()
            y+=square_size
            for i in range(8):
                if self.flags&2**i:
                    cr.set_source_rgb(0,1,0)
                else:
                    cr.set_source_rgb(1,0,0)
                cr.rectangle(x+square_size*i,y,square_size,square_size)
                cr.fill()
            y+= square_size
            cr.set_source_rgb(0.5,0,0.1)
            cr.rectangle(x+square_size*self.bit,y,square_size,square_size)
            cr.fill()
            y+= square_size
        y+= square_size
        cr.move_to(x,y)
        cr.set_source_rgb(0,0,0)
        cr.set_font_size(square_size/1.2)
        cr.show_text(",".join(map(str,self.shape)))
        ltext = ",".join(map(str,self.shape[:self.shape_pos]))
        if ltext:
            ltext+=","
        lx,ly = cr.text_extents(ltext)[-2:]
        w,h = cr.text_extents(",".join(map(str,self.shape[:self.shape_pos+1])))[2:4]
        w-=lx
        h-=ly
        lx+=x
        ly+=y
        cr.rectangle(lx,ly,w,-h)
        cr.set_line_width(square_size/15)
        cr.stroke()
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
    
    def clear_selection(self):
        #self.selected = []
        self.selected_piece = None
        self.selected_pos = None
        self.moves = []
    
    def calculate_shape2d(self):
        width = self.shape[0]
        height = self.shape[1]
        self.shape_2d = []
        x = True
        if len(self.shape)>2:
            self.shape_2d.append(width)
        if len(self.shape)>3:
            self.shape_2d.append(height)
            for sh in self.shape[2:-2]:
                if x:
                    width = width*sh
                    self.shape_2d.append(width)
                    x = False
                else:
                    height = height*sh
                    self.shape_2d.append(height)
                    x = True
            height *= self.shape[-1]
        if len(self.shape)>2:
            width *= self.shape[-2]
        self.width = width
        self.height = height
    
    def check_ctrl(self,target,event,m):
        keyval = event.get_keyval().keyval
        if keyval==Gdk.KEY_Control_L:
            self.ctrl = m
            self.queue_draw()
        elif keyval==Gdk.KEY_Shift_L:
            self.shift = m
    
    def swap_axis(self,axis1,axis2):
        pass
    
    def key_pressed(self,target,event):
        key = event.get_keyval().keyval
        if key==Gdk.KEY_Up:
            if self.ctrl:
                if self.shift:
                    self.flags ^= 2**self.bit
                else:
                    self.piece = (self.piece%self.pieces)+1
            else:
                pass
            self.queue_draw()
        elif key==Gdk.KEY_Down:
            if self.ctrl:
                if self.shift:
                    self.flags ^= 2**self.bit
                else:
                    self.piece = ((self.piece-2)%self.pieces)+1
            self.queue_draw()
        elif key==Gdk.KEY_Left:
            if self.ctrl:
                if self.shift:
                    self.bit = (self.bit-1)%8
                else:
                    self.player = (self.player-1)%self.players
            elif self.shift:
                new_shape_pos = (self.shape_pos-1)%len(self.shape)
                self.swap_axis(self.shape_pos, new_shape_pos)
                self.shape_pos = new_shape_pos
            else:
                self.shape_pos = (self.shape_pos-1)%len(self.shape)
            self.queue_draw()
        elif key==Gdk.KEY_Right:
            if self.ctrl:
                if self.shift:
                    self.bit = (self.bit+1)%8
                else:
                    self.player = (self.player+1)%self.players
            elif self.shift:
                new_shape_pos = (self.shape_pos+1)%len(self.shape)
                self.swap_axis(self.shape_pos, new_shape_pos)
                self.shape_pos = new_shape_pos
            else:
                self.shape_pos = (self.shape_pos+1)%len(self.shape)
            self.queue_draw()
        elif self.ctrl and key==Gdk.KEY_p:
            self.active_player = self.player
    
    def button_pressed(self,target,event):
        wc = screen_to_world((event.x,event.y), self.shape_2d)
        #if self.ctrl:
        #    self.chess.place_piece(wc,self.piece,self.player)
        if self.moves:
            if self.ctrl:
                self.chess.move_piece_low(self.selected_pos,wc)
                self.active_player = (self.active_player+1)%self.players
                self.clear_selection()
            else:
                ind = index_iter(map(get_end,self.moves), wc)
                if ind is not None:
                    self.moves[ind].execute()
                    self.active_player = (self.active_player+1)%self.players
                    self.clear_selection()
                else:
                    it = self.chess.get_all_moves(wc,self.active_player)
                    try:
                        self.selected_piece = next(it)
                        self.moves = list(it)
                        self.selected_pos = wc
                    except StopIteration:
                        self.clear_selection()
        elif self.ctrl:
            self.coords = event.x,event.y
        else:
            it = self.chess.get_all_moves(wc,self.active_player)
            try:
                self.selected_piece = next(it)
                self.moves = list(it)
                self.selected_pos = wc
            except StopIteration:
                pass
        self.queue_draw()
    def button_released(self,target,event):
        if self.ctrl and self.coords is not None:
            x,y = self.coords
            x /= square_size
            y /= square_size
            ex = event.x/square_size
            ey = event.y/square_size
            if x>ex:
                xs = get_all_ints_in_range(ex, x)
            elif x<ex:
                xs = get_all_ints_in_range(x, ex)
            else:
                xs = sg(x)
            if y>ey:
                ys = get_all_ints_in_range(ey, y)
            elif y<ey:
                ys = get_all_ints_in_range(y, ey)
            else:
                ys = sg(y)
            if event.button==3:
                for sc in itertools.product(xs,ys):
                    self.chess.clear_pos(sq_to_world(sc, self.shape_2d))
            else:
                for sc in itertools.product(xs,ys):
                    self.chess.place_piece(sq_to_world(sc, self.shape_2d),self.piece,self.player,self.flags)
            self.queue_draw()
        self.coords = None
                

class widget(Gtk.EventBox):
    def __init__(self,chess,players):
        Gtk.EventBox.__init__(self)
        self.cwidget = lwidget(chess,players)
        self.add(self.cwidget)
        self.set_can_focus(True)
        self.connect("button-press-event",self.cwidget.button_pressed)
        self.connect("button-release-event",self.cwidget.button_released)
        self.connect("key-press-event",self.cwidget.check_ctrl,True)
        self.connect("key-press-event",self.cwidget.key_pressed)
        self.connect("key-release-event",self.cwidget.check_ctrl,False)
    

class window(Gtk.Window):
    def __init__(self,shape,pieces,players):
        Gtk.Window.__init__(self)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
        self.add_events(Gdk.EventMask.KEY_RELEASE_MASK)
        self.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.cwidget = widget(ndchess.ndChess(shape,pieces,players),players)
        self.add(self.cwidget)

if __name__=="__main__":
    shape = ()
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--shape",default="4,4,4,4",type=int_tuple)
    parser.add_argument("--players",default="2",type=int)
    parser.add_argument("--pieces",default="../../../pieces/default.json",type=pieces_file)
    n = parser.parse_args()
    win = window(n.shape,n.pieces,n.players)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
