import numpy
import itertools
import operator
from functools import reduce

field = numpy.dtype([("player",numpy.uint8),("piece",numpy.uint16)])

def inb(a,b):
    return True in map(operator.methodcaller("all"),map(lambda x:x==a,b))

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

class ndChess:
    def __init__(self,shape,allowed_pieces):
        self.shape = shape
        self.allowed_pieces = [None]+list(map(operator.methodcaller("get_in_nd",len(shape)),allowed_pieces))
        self.board = numpy.zeros(shape,dtype=field)
    def place_piece(self,pos,piece,player):
        if isinstance(piece, int):
            self.board[pos]["piece"] = piece
        else:
            self.board[pos]["piece"] = find_piece(piece, self.allowed_pieces)
        self.board[pos]["player"] = player
    def get_piece(self,index):
        return numpy.take(self.allowed_pieces,self.board[index]["piece"])
    def move_piece(self,pos,new_pos,player):
        cont1 = self.board[pos]
        if cont1["piece"] and cont1["player"]==player:
            cont = self.board[new_pos]
            if (not cont["piece"]) or (cont["player"] != player):
                self.board[new_pos] = cont1
                self.board[pos] = b""
                return True
        return False
    def move_piece_high(self,pos,piece,direction,moves,player):
        cont1 = self.board[pos]
        if moves<=piece.max_moves and cont1["piece"] and cont1["player"]==player:
            for i in range(1,moves):
                if self.board[pos+direction*i]["piece"]:
                    return False
            new_pos = pos+direction*moves
            cont = self.board[new_pos]
            if (not cont["piece"]) or (cont["player"] != player):
                self.board[new_pos] = cont1
                self.board[pos] = b""
            

class piece:
    def __init__(self, directions, max_moves=None, auto_generate = True, image=None):
        self.directions = directions
        self.max_moves = max_moves
        self.auto_generate = auto_generate
        self.image = image
        self.children = []
    def get_in_nd(self,n):
        directions = []
        if self.auto_generate:
            for direction in self.directions:
                for sign in itertools.product((True,False),repeat=direction.shape[0]):
                    sdirection = numpy.negative(direction,where=sign,out=direction.copy())
                    for i in itertools.permutations(range(n),sdirection.shape[0]):
                        new_direction = numpy.zeros((n,),dtype=sdirection.dtype)
                        new_direction[i,] = sdirection
                        if not inb(new_direction,directions):
                            directions.append(new_direction)
        else:
            for direction in self.directions:
                new_direction = numpy.zeros((n,))
                new_direction[:direction.shape[0]] = direction
                directions.append(new_direction)
        ret = piece(directions, self.max_moves, self.auto_generate, self.image)
        ret.parent = self
        self.children.append(ret)
        return ret
        