import numpy
import itertools
import operator
from functools import reduce, partial
import json
from os import path
import os

def fileabspath(vpath):
    return path.normpath(path.join(__file__,vpath))

def shellabspath(vpath):
    return path.abspath(path.expandvars(path.expanduser(vpath)))

class PieceJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, piece):
            return {"directions":piece.directions,
                     "max_moves":piece.directions,
                     "auto_generate":piece.auto_generate,
                     "images":piece.images,
                     "start_max_moves":piece.start_max_moves,
                     "capturing":piece.capturing if piece.has_capturing else None}
        elif isinstance(o, numpy.ndarray):
            return o.tolist()
        json.JSONEncoder.default(self, o)

def Piece_object_hook(d):
    if "directions" in d:
        return piece(**{ k:d[k] for k in ["directions","max_moves","auto_generate","images","start_max_moves","capturing"] if k in d})

#field = numpy.dtype([("player",numpy.uint8),("piece",numpy.uint8),("flags",numpy.uint8)])

class field:
    def __init__(self,player=0,piece=0,flags=0):
        self.player = numpy.uint8(player)
        self.piece = numpy.uint8(piece)
        self.flags = numpy.uint8(flags)

class flags(numpy.uint8):
    MOVED = numpy.uint8(2**0)

class Move:
    def __init__(self,start,end,chess):
        self.start = start
        self.end = end
        self.chess = chess
    def execute(self):
        self.chess.move_piece_low(self.start,self.end)

class MoveOP(Move):
    pass

class hashable_array(numpy.ndarray):
    def __hash__(self):
        return int.from_bytes(self.tobytes(),"big")
hashable_array.__eq__ = numpy.array_equal

def ina(a,b):
    for i in a:
        if numpy.array_equal(b, i):
            return True

def find_piece(piece,pieces):
    try:
        return pieces.index(piece)
    except ValueError:
        while hasattr(piece,"parent"):
            piece = piece.parent
            try:
                return pieces.index(piece)
            except ValueError:
                pass
    return find_piece2(piece, pieces)

def find_piece2(piece,pieces):
    for child in piece.children:
        try:
            return pieces.index(child)
        except ValueError:
            r = find_piece2(child,pieces)
            if r:
                return r

def pieces_from_file(file):
    file = path.abspath(file)
    if path.isfile(file):
        wdir = os.getcwd()
        os.chdir(path.dirname(file))
    l = json.load(open(path.abspath(file),"r"),object_hook=Piece_object_hook)
    os.chdir(wdir)
    i = 0
    length = len(l)
    while i<length:
        if not isinstance(l[i], piece):
            l.pop(i)
            length -= 1
        i+=1
    return l

def _get_all_moves(pos,directions,player,max_moves,chess):
    for i in directions:
        if player-1:
            i = -i
        new_pos = pos.copy()
        if max_moves:
            iter = range(max_moves)
        else:
            iter = itertools.repeat(None)
        for j in iter:
            new_pos += i
            if (new_pos<0).any() or (new_pos>=chess.shape).any():
                break
            try:
                cont2 = chess.board[new_pos]
            except KeyError:
                yield Move(pos,new_pos.copy(),chess)
                continue
            if cont2.player==player:
                break
            yield Move(pos,new_pos.copy(),chess)
            if cont2.piece:
                break

def _get_capturing_moves(pos,directions,player,max_moves,chess):
    for i in directions:
        if player-1:
            i = -i
        new_pos = pos.copy()
        if max_moves:
            iter = range(max_moves)
        else:
            iter = itertools.repeat(None)
        for j in iter:
            new_pos += i
            if (new_pos<0).any() or (new_pos>=chess.shape).any():
                break
            try:
                cont2 = chess.board[new_pos]
            except KeyError:
                continue
            if cont2.player==player:
                break
            if cont2.piece:
                yield Move(pos,new_pos.copy(),chess)
                break

def _get_noncapturing_moves(pos,directions,player,max_moves,chess):
    for i in directions:
        if player-1:
            i = -i
        new_pos = pos.copy()
        if max_moves:
            iter = range(max_moves)
        else:
            iter = itertools.repeat(None)
        for j in iter:
            new_pos += i
            if (new_pos<0).any() or (new_pos>=chess.shape).any():
                break
            try:
                cont2 = chess.board[new_pos]
            except KeyError:
                yield Move(pos,new_pos.copy(),chess)
                continue
            if cont2.player==player or cont2.piece:
                break
            yield Move(pos,new_pos.copy(),chess)

class ndChess:
    def __init__(self,shape,allowed_pieces):
        self.shape = numpy.array(shape,copy=False)
        self.allowed_pieces = [None]+list(map(operator.methodcaller("get_in_nd",len(shape)),allowed_pieces))
        #self.board = numpy.zeros(shape,dtype=field)
        self.board = {}
        self.king_positions = set()
        self.turn = 1
    def place_piece(self,pos,piece,player,flags=0):
        pos = numpy.array(pos,copy=False).view(hashable_array)
        if not isinstance(piece, int):
            piece = find_piece(piece, self.allowed_pieces)
        try:
            cont = self.board[pos]
            if cont.piece==1:
                self.king_positions.discard((pos,cont.player))
            cont.piece = piece
            cont.player = player
            cont.flags = flags
        except KeyError:
            self.board[pos] = field(player, piece, flags)
        if piece==1:
            self.king_positions.add((pos,player))
    def place_piece_field(self,pos,field):
        pos = numpy.array(pos,copy=False).view(hashable_array)
        try:
            cont = self.board[pos]
            if cont.piece==1:
                self.king_positions.discard((pos,cont.player))
        except KeyError:
            pass
        self.board[pos] = field
        if field.piece==1:
            self.king_positions.add((pos,field.player))
    def clear_pos(self,pos):
        pos = numpy.array(pos,copy=False).view(hashable_array)
        try:
            cont = self.board[pos]
        except KeyError:
            return
        if cont.piece==1:
            self.king_positions.remove((pos,cont.player))
        del self.board[pos]
    def move_piece_low(self,pos,new_pos):
        pos = numpy.array(pos,copy=False).view(hashable_array)
        try:
            cont = self.board[pos]
        except KeyError:
            return
        cont.flags |= flags.MOVED
        self.place_piece_field(new_pos, cont)
        self.clear_pos(pos)
    
    # TODO
    def is_check(self,player):
        for wc in itertools.product(*map(range,self.board.shape)):
            cont = self.board[wc]
            wc = numpy.array(wc)
            pp = cont["player"]
            if cont["piece"] and pp!=player:
                piece = self.allowed_pieces[cont["piece"]]
                if not cont["flags"]&flags.MOVED:
                    max_moves = piece.start_max_moves
                else:
                    max_moves = piece.max_moves
                if piece.has_capturing:
                    for i in piece.capturing:
                        j = 1
                        while j<=max_moves:
                            pos = wc+i*j
                            if (pos<0).any():
                                break
                            try:
                                cont2 = self.board[tuple(pos)]
                            except IndexError:
                                break
                            if cont2["player"]==pp:
                                break
                            if cont2["piece"]==1 and cont2["player"]==player:
                                return piece
                            if cont2["piece"]:
                                break
                            j+=1
                else:
                    for i in piece.directions:
                        j = 1
                        while j<=max_moves:
                            pos = wc+i*j
                            if (pos<0).any():
                                break
                            try:
                                cont2 = self.board[tuple(pos)]
                            except IndexError:
                                break
                            if cont2["player"]==pp:
                                break
                            if cont2["piece"]==1 and cont2["player"]==player:
                                return piece
                            if cont2["piece"]:
                                break
                            j+=1
    def get_all_moves(self,pos,player):
        pos = numpy.array(pos,copy=False).view(hashable_array)
        if pos in self.board:
            cont = self.board[pos]
            if cont.piece and cont.player==player:
                piece = self.allowed_pieces[cont.piece]
                max_moves = piece.max_moves if cont.flags&flags.MOVED else piece.start_max_moves
                yield piece
                if piece.has_capturing:
                    yield from _get_noncapturing_moves(pos, piece.directions, player, max_moves, self)
                    yield from _get_capturing_moves(pos, piece.capturing, player, max_moves, self)
                else:
                    yield from _get_all_moves(pos, piece.directions, player, max_moves, self)
        else:
            return

def extend(v,dims):
    for sign in itertools.product((True,False),repeat=v.shape[0]):
        sdirection = numpy.negative(v,where=sign,out=v.copy())
        for i in itertools.permutations(range(dims),sdirection.shape[0]):
            new_direction = numpy.zeros((dims,),dtype=sdirection.dtype)
            new_direction[i,] = sdirection
            yield new_direction
    

class piece:
    def __init__(self, directions, max_moves=None, auto_generate = True, images=[], start_max_moves=None, capturing=None):
        self.directions = list(map(partial(numpy.array,dtype=numpy.int8),directions))
        self.max_moves = max_moves
        self.auto_generate = auto_generate
        self.images = list(map(path.abspath,images))
        self.children = []
        if start_max_moves is None:
            self.start_max_moves = self.max_moves
        else:
            self.start_max_moves = start_max_moves
        if capturing is None:
            self.has_capturing = False
        else:
            self.has_capturing = True
            self.capturing = list(map(numpy.array,capturing))
    @classmethod
    def from_values(cls,directions, max_moves, auto_generate, images, start_max_moves, has_capturing, capturing=None):
        self = cls.__new__(cls)
        self.directions = directions
        self.max_moves = max_moves
        self.auto_generate = auto_generate
        self.images = images
        self.start_max_moves = start_max_moves
        self.has_capturing = has_capturing
        if has_capturing:
            if capturing is None:
                raise ValueError("no capturing given")
            else:
                self.capturing = capturing
        return self
    def get_in_nd(self,n):
        directions = []
        if self.has_capturing:
            capturing = []
        else:
            capturing = None
        if self.auto_generate:
            for direction in self.directions:
                for new_direction in extend(direction, n):
                    if not ina(directions,new_direction):
                        directions.append(new_direction)
            if self.has_capturing:
                for capturingn in self.capturing:
                    for new_capturing in extend(capturingn, n):
                        if not ina(capturing,new_capturing):
                            capturing.append(new_capturing)
        else:
            for direction in self.directions:
                new_direction = numpy.zeros((n,),dtype=direction.dtype)
                new_direction[:direction.shape[0]] = direction
                directions.append(new_direction)
            if self.has_capturing:
                for direction in self.capturing:
                    new_direction = numpy.zeros((n,),dtype=direction.dtype)
                    new_direction[:direction.shape[0]] = direction
                    capturing.append(new_direction)
        ret = piece.from_values(directions, self.max_moves, self.auto_generate, self.images, self.start_max_moves, self.has_capturing, capturing)
        ret.parent = self
        self.children.append(ret)
        return ret
        