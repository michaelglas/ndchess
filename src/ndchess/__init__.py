import numpy
import itertools
import operator
from functools import reduce
import json
from os import path
import os

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

field = numpy.dtype([("player",numpy.uint8),("piece",numpy.uint8),("flags",numpy.uint8)])

class flags(int):
    MOVED = 2**0

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

def _get_all_moves(pos,directions,board,player,max_moves):
    for i in directions:
        j = 1
        new_pos = pos.copy()
        while j<=max_moves:
            new_pos += i
            if (new_pos<0).any():
                break
            try:
                cont2 = board[tuple(new_pos)]
            except IndexError:
                break
            if cont2["player"]==player:
                break
            yield new_pos.copy()
            if cont2["piece"]:
                break
            j+=1

def _get_capturing_moves(pos,directions,board,player,max_moves):
    for i in directions:
        j = 1
        new_pos = pos.copy()
        while j<=max_moves:
            new_pos += i
            if (new_pos<0).any():
                break
            try:
                cont2 = board[tuple(new_pos)]
            except IndexError:
                break
            if cont2["player"]==player:
                break
            if cont2["piece"]:
                yield new_pos.copy()
                break
            j+=1

def _get_noncapturing_moves(pos,directions,board,player,max_moves):
    for i in directions:
        j = 1
        new_pos = pos.copy()
        while j<=max_moves:
            new_pos += i
            if (new_pos<0).any():
                break
            try:
                cont2 = board[tuple(new_pos)]
            except IndexError:
                break
            if cont2["player"]==player or cont2["piece"]:
                break
            yield new_pos.copy()
            j+=1

class ndChess:
    def __init__(self,shape,allowed_pieces):
        self.shape = shape
        self.allowed_pieces = [None]+list(map(operator.methodcaller("get_in_nd",len(shape)),allowed_pieces))
        self.board = numpy.zeros(shape,dtype=field)
        self.king_positions = set()
        self.turn = 1
    def place_piece(self,pos,piece,player):
        if not isinstance(piece, int):
            piece = find_piece(piece, self.allowed_pieces)
        self.board[pos]["piece"] = piece
        if piece==1:
            self.king_positions.add((numpy.array(pos).view(hashable_array),player))
        self.board[pos]["player"] = player
        self.board[pos]["flags"] = 0
    def get_piece(self,index):
        return numpy.take(self.allowed_pieces,self.board[index]["piece"])
    def move_piece(self,pos,new_pos,player):
        cont1 = self.board[tuple(pos)]
        if cont1["piece"] and cont1["player"]==player:
            cont = self.board[tuple(new_pos)]
            if (not cont["piece"]) or (cont["player"] != player):
                self.board[new_pos] = cont1
                self.board[new_pos]["flags"] |= flags.MOVED
                self.board[pos] = b""
                self.turn += 1
                if cont["piece"]==1:
                    self.king_positions.discard((pos.view(hashable_array),player))
                    self.king_positions.add((new_pos.view(hashable_array),player))
                return True
        return False
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
    def is_checkmate(self,player):
        coords = set(map(operator.methodcaller("view",hashable_array),itertools.chain.from_iterable(map(lambda x:self.get_all_moves(x[0], player),filter(lambda x:x[1]==player,self.king_positions)))))
        print(coords)
    def get_all_moves(self,pos,player):
        if not self.board[tuple(pos)]["flags"]&flags.MOVED:
            return self.get_all_moves_start(pos, player)
        else:
            return self._get_all_movesg(pos, player)
    def _get_all_movesg(self,pos,player):
        cont = self.board[tuple(pos)]
        if cont["piece"] and cont["player"]==player:
            piece = self.allowed_pieces[cont["piece"]]
            yield piece
            if piece.has_capturing:
                yield from _get_noncapturing_moves(pos, piece.directions, self.board, player, piece.max_moves)
                yield from _get_capturing_moves(pos, piece.capturing, self.board, player, piece.max_moves)
            else:
                yield from _get_all_moves(pos, piece.directions, self.board, player, piece.max_moves)
                    
    def get_all_moves_start(self,pos,player):
        cont = self.board[tuple(pos)]
        if cont["piece"] and cont["player"]==player:
            piece = self.allowed_pieces[cont["piece"]]
            yield piece
            if piece.has_capturing:
                yield from _get_noncapturing_moves(pos, piece.directions, self.board, player, piece.start_max_moves)
                yield from _get_capturing_moves(pos, piece.capturing, self.board, player, piece.max_moves)
            else:
                yield from _get_all_moves(pos, piece.directions, self.board, player, piece.start_max_moves)

def extend(v,dims):
    for sign in itertools.product((True,False),repeat=v.shape[0]):
        sdirection = numpy.negative(v,where=sign,out=v.copy())
        for i in itertools.permutations(range(dims),sdirection.shape[0]):
            new_direction = numpy.zeros((dims,),dtype=sdirection.dtype)
            new_direction[i,] = sdirection
            yield new_direction
    

class piece:
    def __init__(self, directions, max_moves=float("inf"), auto_generate = True, images=[], start_max_moves=None, capturing=None):
        self.directions = list(map(numpy.array,directions))
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
                new_direction = numpy.zeros((n,))
                new_direction[:direction.shape[0]] = direction
                directions.append(new_direction)
            if self.has_capturing:
                for direction in self.capturing:
                    new_direction = numpy.zeros((n,))
                    new_direction[:direction.shape[0]] = direction
                    directions.append(new_direction)
        ret = piece.from_values(directions, self.max_moves, self.auto_generate, self.images, self.start_max_moves, self.has_capturing, capturing)
        ret.parent = self
        self.children.append(ret)
        return ret
        