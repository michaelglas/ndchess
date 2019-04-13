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
        return piece(**{ k:d[k] for k in ["directions","max_moves","auto_generate","images","start_max_moves","capturing","player_dependent_axis"] if k in d})

#field = numpy.dtype([("player",numpy.uint8),("piece",numpy.uint8),("flags",numpy.uint8)])

class field:
    def __init__(self,player=0,piece=0,flags=0):
        self.player = numpy.uint8(player)
        self.piece = numpy.uint8(piece)
        self.flags = numpy.uint8(flags)

class capture_marker:
    def __init__(self,link):
        self.link = link

class flags(numpy.uint8):
    MOVED = numpy.uint8(2**0)

class Move:
    def __init__(self,start,end,chess):
        self.start = start
        self.end = end
        self.chess = chess
    def execute(self):
        self.chess.move_piece_low(self.start,self.end)
        self.chess.clear_capturing_markers()

class MoveEP(Move):
    def __init__(self,start,end,cm,chess):
        self.start = start
        self.end = end
        self.capt_mark = cm
        self.chess = chess
    def execute(self):
        Move.execute(self)
        self.chess.clear_capturing_markers()
        self.chess.place_capture_marker(self.capt_mark,self.end)
        

def get_as_player(dir,player,axis,out=None):
    if out is None:
        out = dir.copy()
    else:
        out[...] = dir
    a2=(player//2)%dir.shape[-1]
    if a2:
        if a2<=axis:
            a2-=1
        temp = out[...,axis].copy()
        out[...,axis]=out[...,a2]
        out[...,a2]=temp
    if player&1:
        numpy.negative(out,out=out)
    return out

def get_permutations(n,k):
    p = n
    for i in range(1,k):
        p*=n-i
    return p

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

def _check_all(pos,piece,player,chess):
    if (pos<0).any() or (pos>=chess.shape).any():
        return False,True
    try:
        cont2 = chess.board[pos]
    except KeyError:
        return True,False
    if type(cont2)==capture_marker:
        linkcont = chess.board[cont2.link]
        if linkcont.player!=player and linkcont.piece==piece:
            return True,True
        else:
            return True,False
    if cont2.player==player:
        return False,True
    return True,True

def _check_capturing(pos,piece,player,chess):
    if (pos<0).any() or (pos>=chess.shape).any():
        return False,True
    try:
        cont2 = chess.board[pos]
    except KeyError:
        return False,False
    if type(cont2)==capture_marker:
        linkcont = chess.board[cont2.link]
        if linkcont.player!=player and linkcont.piece==piece:
            return True,True
        else:
            return False,False
    if cont2.player==player:
        return False,True
    return True,True

def _check_noncapturing(pos,piece,player,chess):
    if (pos<0).any() or (pos>=chess.shape).any():
        return False,True
    try:
        cont2 = chess.board[pos]
    except KeyError:
        return True,False
    if type(cont2)==capture_marker:
        linkcont = chess.board[cont2.link]
        if linkcont.player!=player and linkcont.piece==piece:
            return False,True
        else:
            return True,False
    if cont2.player==player:
        return False,True
    return False,True

def _get_all_moves(pos,directions,player,max_moves,chess,piece):
    if max_moves:
        iter = range(max_moves)
    else:
        iter = itertools.repeat(None)
    for i in directions:

        new_pos = pos.copy()
        for j in iter:
            new_pos += i
            """
            if (new_pos<0).any() or (new_pos>=chess.shape).any():
                break
            try:
                cont2 = chess.board[new_pos]
            except KeyError:
                yield Move(pos,new_pos.copy(),chess)
                continue
            if type(cont2)==capture_marker:
                yield Move(pos,new_pos.copy(),chess)
                if cont2.link.player!=player and cont2.link.piece==piece:
                    break
                continue
            if cont2.player==player:
                break
            yield Move(pos,new_pos.copy(),chess)
            if cont2.piece:
                break
            """
            r,b = _check_all(new_pos, piece, player, chess)
            if r:
                yield Move(pos,new_pos.copy(),chess)
            if b:
                break

def _get_all_moves_start(pos,directions,player,max_moves,start_max_moves,chess,piece):
    if max_moves:
        if start_max_moves:
            if start_max_moves>max_moves:
                siter = range(max_moves,start_max_moves)
                iter = range(max_moves)
            else:
                yield from _get_all_moves(pos, directions, player, start_max_moves, chess, piece)
                return
        else:
            siter = itertools.repeat(None)
            iter = range(max_moves)
    else:
        if start_max_moves:
            yield from _get_all_moves(pos, directions, player, start_max_moves, chess, piece)
            return
        yield from _get_all_moves(pos, directions, player, None, chess, piece)
        return
    
    for i in directions:
        new_pos = pos.copy()
        for j in iter:
            new_pos += i
            r,b = _check_all(new_pos, piece, player, chess)
            if r:
                yield Move(pos,new_pos.copy(),chess)
            if b:
                break
        cm = new_pos.copy()
        for j in siter:
            new_pos += i
            r,b = _check_all(new_pos, piece, player, chess)
            if r:
                yield MoveEP(pos,new_pos.copy(),cm,chess)
            if b:
                break

def _get_capturing_moves(pos,directions,player,max_moves,chess,piece):
    if max_moves:
        iter = range(max_moves)
    else:
        iter = itertools.repeat(None)
    for i in directions:
        new_pos = pos.copy()
        for j in iter:
            new_pos += i
            r,b = _check_capturing(new_pos, piece, player, chess)
            if r:
                yield Move(pos,new_pos.copy(),chess)
            if b:
                break

def _get_capturing_moves_start(pos,directions,player,max_moves,start_max_moves,chess,piece):
    if max_moves:
        if start_max_moves:
            if start_max_moves>max_moves:
                siter = range(max_moves,start_max_moves)
                iter = range(max_moves)
            else:
                yield from _get_capturing_moves(pos, directions, player, start_max_moves, chess)
                return
        else:
            siter = itertools.repeat(None)
            iter = range(max_moves)
    else:
        if start_max_moves:
            yield from _get_capturing_moves(pos, directions, player, start_max_moves, chess)
            return
        yield from _get_capturing_moves(pos, directions, player, None, chess)
        return
    
    for i in directions:
        new_pos = pos.copy()
        for j in iter:
            new_pos += i
            r,b = _check_capturing(new_pos, piece, player, chess)
            if r:
                yield Move(pos,new_pos.copy(),chess)
            if b:
                break
        cm = new_pos.copy()
        for j in siter:
            new_pos += i
            r,b = _check_capturing(new_pos, piece, player, chess)
            if r:
                yield MoveEP(pos,new_pos.copy(),cm,chess)
            if b:
                break

def _get_noncapturing_moves(pos,directions,player,max_moves,chess,piece):
    if max_moves:
        iter = range(max_moves)
    else:
        iter = itertools.repeat(None)
    for i in directions:
        new_pos = pos.copy()
        for j in iter:
            new_pos += i
            r,b = _check_noncapturing(new_pos, piece, player, chess)
            if r:
                yield Move(pos,new_pos.copy(),chess)
            if b:
                break


def _get_noncapturing_moves_start(pos,directions,player,max_moves,start_max_moves,chess,piece):
    if max_moves:
        if start_max_moves:
            if start_max_moves>max_moves:
                siter = range(max_moves,start_max_moves)
                iter = range(max_moves)
            else:
                yield from _get_noncapturing_moves(pos, directions, player, start_max_moves, chess, piece)
                return
        else:
            siter = itertools.repeat(None)
            iter = range(max_moves)
    else:
        if start_max_moves:
            yield from _get_noncapturing_moves(pos, directions, player, start_max_moves, chess, piece)
            return
        yield from _get_noncapturing_moves(pos, directions, player, None, chess, piece)
        return
    
    for i in directions:
        new_pos = pos.copy()
        for j in iter:
            new_pos += i
            r,b = _check_noncapturing(new_pos, piece, player, chess)
            if r:
                yield Move(pos,new_pos.copy(),chess)
            if b:
                break
        cm = new_pos.copy()
        for j in siter:
            new_pos += i
            r,b = _check_noncapturing(new_pos, piece, player, chess)
            if r:
                yield MoveEP(pos,new_pos.copy(),cm,chess)
            if b:
                break

class ndChess:
    def __init__(self,shape,allowed_pieces,players):
        self.shape = numpy.array(shape,copy=False)
        self.allowed_pieces = [None]+list(map(operator.methodcaller("get_in_nd",len(shape),players),allowed_pieces))
        self.board = {}
        self.king_positions = set()
        self.capturing_markers = set()
        self.turn = 1
    def place_capture_marker(self,pos,link):
        pos = numpy.array(pos,copy=False).view(hashable_array)
        if link in self.board and isinstance(self.board[link], field):
            if pos in self.board:
                if isinstance(self.board[pos], capture_marker):
                    self.capturing_markers.add(pos)
                    self.board[pos] = capture_marker(link)
            else:
                self.capturing_markers.add(pos)
                self.board[pos] = capture_marker(link)
    def clear_capturing_markers(self):
        for i in self.capturing_markers:
            del self.board[i]
        self.capturing_markers.clear()
    def place_piece(self,pos,piece,player,flags=0):
        pos = numpy.array(pos,copy=False).view(hashable_array)
        if not isinstance(piece, int):
            piece = find_piece(piece, self.allowed_pieces)
        try:
            cont = self.board[pos]
            if isinstance(cont, field):
                if cont.piece==1:
                    self.king_positions.discard((pos,cont.player))
            elif isinstance(cont, capture_marker):
                self.capturing_markers.discard(pos)
                self.clear_pos(cont.link)
        except KeyError:
            pass
        self.board[pos] = field(player, piece, flags)
        if piece==1:
            self.king_positions.add((pos,player))
    def place_piece_field(self,pos,fieldv):
        pos = numpy.array(pos,copy=False).view(hashable_array)
        try:
            cont = self.board[pos]
            if isinstance(cont, field) and cont.piece==1:
                self.king_positions.discard((pos,cont.player))
            elif isinstance(cont, capture_marker):
                self.capturing_markers.discard(pos)
                self.clear_pos(cont.link)
        except KeyError:
            pass
        self.board[pos] = fieldv
        if fieldv.piece==1:
            self.king_positions.add((pos,fieldv.player))
    def clear_pos(self,pos):
        pos = numpy.array(pos,copy=False).view(hashable_array)
        try:
            cont = self.board[pos]
        except KeyError:
            return
        if isinstance(cont, field):
            if cont.piece==1:
                self.king_positions.remove((pos,cont.player))
        else:
            self.capturing_markers.discard(pos)
        del self.board[pos]
    def move_piece_low(self,pos,new_pos):
        pos = numpy.array(pos,copy=False).view(hashable_array)
        try:
            cont = self.board[pos]
        except KeyError:
            return
        if isinstance(cont, field):
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
            if isinstance(cont, field) and cont.player==player:
                piece = self.allowed_pieces[cont.piece]
                #max_moves = piece.max_moves if cont.flags&flags.MOVED else piece.start_max_moves
                yield piece
                if cont.flags&flags.MOVED:
                    if piece.has_capturing:
                        if piece.player_dependent:
                            yield from _get_noncapturing_moves(pos, piece.directions[player], player, piece.max_moves, self, cont.piece)
                            yield from _get_capturing_moves(pos, piece.capturing[player], player, piece.max_moves, self, cont.piece)
                        else:
                            yield from _get_noncapturing_moves(pos, piece.directions, player, piece.max_moves, self, cont.piece)
                            yield from _get_capturing_moves(pos, piece.capturing, player, piece.max_moves, self, cont.piece)
                    else:
                        if piece.player_dependent:
                            yield from _get_all_moves(pos, piece.directions[player], player, piece.max_moves, self, cont.piece)
                        else:
                            yield from _get_all_moves(pos, piece.directions, player, piece.max_moves, self, cont.piece)
                else:
                    if piece.has_capturing:
                        if piece.player_dependent:
                            yield from _get_noncapturing_moves_start(pos, piece.directions[player], player, piece.max_moves, piece.start_max_moves, self, cont.piece)
                            yield from _get_capturing_moves(pos, piece.capturing[player], player, piece.max_moves, self, cont.piece)
                        else:
                            yield from _get_noncapturing_moves_start(pos, piece.directions, player, piece.max_moves, piece.start_max_moves, self, cont.piece)
                            yield from _get_capturing_moves(pos, piece.capturing, player, piece.max_moves, self, cont.piece)
                    else:
                        if piece.player_dependent:
                            yield from _get_all_moves_start(pos, piece.directions[player], player, piece.max_moves, piece.start_max_moves, self, cont.piece)
                        else:
                            yield from _get_all_moves_start(pos, piece.directions, player, piece.max_moves, piece.start_max_moves, self, cont.piece)
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
    def __init__(self, directions, max_moves=None, auto_generate = True, images=[], start_max_moves=None, capturing=None, player_dependent_axis=None):
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
        if player_dependent_axis is None:
            self.player_dependent = False
        else:
            self.player_dependent_axis=player_dependent_axis
            self.player_dependent = True
    @classmethod
    def from_values(cls,directions, max_moves, auto_generate, images, start_max_moves, has_capturing, player_dependent, player_dependent_axis=None, capturing=None):
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
        self.player_dependent = player_dependent
        if player_dependent:
            if player_dependent_axis is None:
                raise ValueError("no player dependent axis given")
            else:
                self.player_dependent_axis = player_dependent_axis
        return self
    def get_in_nd(self,n,players=1):
        #directions = []
        if self.player_dependent:
            directions = numpy.empty((players,sum(((2**i.shape[0])*get_permutations(n, i.shape[0]) for i in self.directions)) if self.auto_generate else len(self.directions),n),dtype=numpy.int8)
        else:
            directions = numpy.empty((1,sum(((2**i.shape[0])*get_permutations(n, i.shape[0]) for i in self.directions)) if self.auto_generate else len(self.directions),n),dtype=numpy.int8)
        dlength = 0
        if self.has_capturing:
            if self.player_dependent:
                capturing = numpy.empty((players,sum(((2**i.shape[0])*get_permutations(n, i.shape[0]) for i in self.capturing)) if self.auto_generate else len(self.capturing),n),dtype=numpy.int8)
            else:
                capturing = numpy.empty((1,sum(((2**i.shape[0])*get_permutations(n, i.shape[0]) for i in self.capturing)) if self.auto_generate else len(self.capturing),n),dtype=numpy.int8)
            clength = 0
        else:
            capturing = None
        if self.auto_generate:
            for direction in self.directions:
                for new_direction in extend(direction, n):
                    if not ina(directions[0,:dlength,:],new_direction):
                        directions[0,dlength] = new_direction
                        dlength+=1
            if self.has_capturing:
                for capturingn in self.capturing:
                    for new_capturing in extend(capturingn, n):
                        if not ina(capturing[0,:clength,:],new_capturing):
                            capturing[0,clength] = new_capturing
                            clength+=1
        else:
            for direction in self.directions:
                new_direction = numpy.zeros((n,),dtype=direction.dtype)
                new_direction[:direction.shape[0]] = direction
                directions[0,dlength] = new_direction
                dlength+=1
            if self.has_capturing:
                for capturingn in self.capturing:
                    new_capturing = numpy.zeros((n,),dtype=capturingn.dtype)
                    new_capturing[:capturingn.shape[0]] = capturingn
                    capturing[0,clength] = new_capturing
                    clength+=1
        if self.player_dependent:
            directions.resize((players,dlength,n))
        else:
            directions.resize((dlength,n))
        if self.has_capturing:
            if self.player_dependent:
                capturing.resize((players,clength,n))
            else:
                capturing.resize((clength,n))
        if self.player_dependent:
            dir = directions[0]
            for i in range(1,players):
                get_as_player(dir, i, self.player_dependent_axis, out=directions[i])
            if self.has_capturing:
                cap = capturing[0]
                for i in range(1,players):
                    get_as_player(cap, i, self.player_dependent_axis, out=capturing[i])
        ret = piece.from_values(directions, self.max_moves, self.auto_generate, self.images, self.start_max_moves, self.has_capturing, self.player_dependent, self.player_dependent_axis if self.player_dependent else None, capturing)
        ret.parent = self
        self.children.append(ret)
        return ret
        