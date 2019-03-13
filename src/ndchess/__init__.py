import numpy
import itertools
import operator
from functools import reduce

field = numpy.dtype([("player",numpy.uint8),("piece",numpy.uint16)])

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

class ndChess:
    def __init__(self,shape,allowed_pieces):
        self.shape = shape
        self.allowed_pieces = [None]+list(map(operator.methodcaller("get_in_nd",len(shape)),allowed_pieces))
        self.board = numpy.zeros(shape,dtype=field)
        self.king_positions = set()
    def place_piece(self,pos,piece,player):
        if not isinstance(piece, int):
            piece = find_piece(piece, self.allowed_pieces)
        self.board[pos]["piece"] = piece
        if piece==1:
            self.king_positions.add(numpy.array(pos).view(hashable_array))
        self.board[pos]["player"] = player
    def get_piece(self,index):
        return numpy.take(self.allowed_pieces,self.board[index]["piece"])
    def move_piece(self,pos,new_pos,player):
        cont1 = self.board[tuple(pos)]
        if cont1["piece"] and cont1["player"]==player:
            cont = self.board[tuple(new_pos)]
            if (not cont["piece"]) or (cont["player"] != player):
                self.board[new_pos] = cont1
                self.board[pos] = b""
                if cont["piece"]==1:
                    self.king_positions.discard(pos.view(hashable_array))
                    self.king_positions.add(new_pos.view(hashable_array))
                return True
        return False
    def is_check(self,player):
        for wc in itertools.product(*map(range,self.board.shape)):
            cont = self.board[wc]
            wc = numpy.array(wc)
            pp = cont["player"]
            if cont["piece"] and pp!=player:
                piece = self.allowed_pieces[cont["piece"]]
                for i in piece.directions:
                    j = 1
                    while j<=piece.max_moves:
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
                            return True
                        if cont2["piece"]:
                            break
                        j+=1
        return False
    def is_checkmate(self,player):
        coords = set(map(operator.methodcaller("view",hashable_array),itertools.chain.from_iterable(map(lambda x:self.get_all_moves(x, player),self.king_positions))))
        print(coords)
    def get_all_moves(self,pos,player):
        cont = self.board[tuple(pos)]
        if cont["piece"] and cont["player"]==player:
            piece = self.allowed_pieces[cont["piece"]]
            for i in piece.directions:
                j = 1
                while j<=piece.max_moves:
                    pos = pos+i*j
                    if (pos<0).any():
                        break
                    try:
                        cont2 = self.board[tuple(pos)]
                    except IndexError:
                        break
                    if cont2["player"]==player:
                        break
                    yield pos
                    if cont2["piece"]:
                        break
                    j+=1

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
                        if not ina(directions,new_direction):
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
        