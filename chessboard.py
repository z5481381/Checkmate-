import asyncio
from bleak import BleakScanner
from bleak import BleakClient
import copy
from stockfish import Stockfish # type: ignore
STOCKFISH_PATH = "stockfish\stockfish-windows-x86-64-avx2"
stockfish = Stockfish(path=STOCKFISH_PATH, depth=15)
import time
import chess
import chess.engine
from dataclasses import dataclass

# Value of toMove if White
WHITE = 1
# Value of toMove if Black
BLACK = 0
# Amount of spaces required 
FENSPACESFOREP = 3

class BoardState:
        def __init__(self, hex_rep, arr, toMove, fen, computerSide, mode):
            self.hex_rep = hex_rep
            self.arr = arr 
            self.toMove = toMove
            self.fen = fen
            self.computerSide = computerSide
            self.mode = mode
    # Create the piece class
class Piece:
        def __init__(self, name, side):
            self.name = name
            self.side = side
# led class
@dataclass
class ledVal:
    row: int
    col: int
    r: int
    g: int
    b: int

# list of led classes
ledData = []

prev_board_state = None
curr_board_state = None
computerSide = None
blank_square = Piece("", "")
whiteCastlingAvailable = ['K', 'Q']
blackCastlingAvailable = ['k', 'q']
enPassantMovesAvailable = []
halfMovesSinceCaptureOrPawnMove = 0
movesInGame = 1
liftedPieceHexRep = None

target_name = "Checkmate+"
target_address = None
    
SERVICE_UUID     =   "22c2b227-b1b7-4a09-babb-e1d6b701183d"
BOARD_STATE_UUID =   "7a96b8e3-41bc-428d-8f52-5601235c2dca"
LED_ROW_UUID     =   "7d4a35e3-84b4-42b3-b279-5d9b9f28f5fd"
LED_COL_UUID     =   "56d86c37-0273-4671-b8c0-e0fe74e1b4c0"
LED_R_UUID       =   "0f5a6555-250d-41f8-b318-7a0ff4737169"
LED_G_UUID       =   "738ea3b6-8ccc-4b19-a3da-48149c95b74f"
LED_B_UUID       =   "bc424431-dd9b-4cda-a1ab-5cbc8f62388c"
DONE_UUID        =   "4657f152-f696-4bfa-96f2-0f9e932a7319"
LCD_UUID      =    "aee33363-c3d9-49c0-b7e5-d0d58339c687"
doneVal = 0

async def main():
    global target_name, target_address, SERVICE_UUID, BOARD_STATE_UUID, LED_UUID
    # Initialise Board
    init_board()
    # await run_chessboard_simulation(client)
    # Searches for bluetooth device

    devices = await BleakScanner.discover()
    for d in devices:
        print(d)
        if target_name == d.name:
            target_address = d.address
            print("found target {} bluetooth device with address {} ".format(target_name,target_address))
            break

    if target_address is not None:        
        async with BleakClient(target_address) as client:
            print(f"Connected: {client.is_connected}")

        # Asks the player if they want to play on board or online

            singleOrMultiPlayer = input(
            "Are you playing online or on the board?\n"
            "Reply 'o' for Online and 'b' for the board: "
            )

            if (singleOrMultiPlayer == 'b'):
                temp = None
                while 1:
                # send example
                # wait client.write_gatt_char(LED_UUID, bytes(text, 'UTF-8'), response=True)
                    
                # read example
                    try:
                        await lcdScreen(client)
                        input("Continue?")
                        data_from_controller = await client.read_gatt_char(BOARD_STATE_UUID)
                        data_decoded = data_from_controller.decode('utf-8') #convert byte to str
                        data = int(data_decoded)
                        # Checking if data is 16 bits else Invalid Input
                        if(temp == data):
                            continue
                        elif (0 <= data <= 0xffffffffffffffff):
                            await checkAndUpdateState(data, client)
                            temp = data 
                            print_board(curr_board_state.arr)
                            print(curr_board_state.fen)
                        # Evaluate Checkmate
                            if evaluatePosition(curr_board_state.fen):
                                break
                        else:
                            print("Invalid Input")
                            # print("data: {}".format(data))
                    except Exception as err:
                        print(Exception, err)
            elif(singleOrMultiPlayer == 'o'):
                temp = None   
                while 1:
                    computerSide = input("Are you playing with White or Black: ")

                    if (computerSide == "White"):
                        computerSide = WHITE
                        break
                    elif(computerSide == "Black"):
                        computerSide = BLACK
                        break
                    else:
                        print("Invalid Side. Try Again")
            
                while 1:
                    if(computerSide == curr_board_state.toMove):
                        move_data = input("What is your move: ")
                        stockfish.set_fen_position(curr_board_state.fen)
                        if (stockfish.is_move_correct(move_data)):
                            stockfish.make_moves_from_current_position([move_data])
                            await computerUpdateState(stockfish.get_fen_position(), move_data, client)
                            print_board(curr_board_state.arr)
                        else:
                            continue
                    else:
                        try:
                            data_from_controller = await client.read_gatt_char(BOARD_STATE_UUID)
                            data_decoded = data_from_controller.decode('utf-8') #convert byte to str
                            data = int(data_decoded)
                            # Checking if data is 16 bits else Invalid Input
                            if(temp == data):
                                continue
                            elif (0 <= data <= 0xffffffffffffffff):
                                await checkAndUpdateState(data, client)
                                temp = data 
                                print_board(curr_board_state.arr)
                                print(curr_board_state.fen)
                        # Evaluate Checkmate
                                if evaluatePosition(curr_board_state.fen):
                                    break
                            else:
                                print("Invalid Input")
                            # print("data: {}".format(data))
                        except Exception:
                            pass
            else:
                print("Not a valid input!")                           
    else:
        print("could not find target bluetooth device nearby")


def checkValidMove(diff):
    from_i, from_j, i, j = findingSquares(diff)
    if not curr_board_state.arr[from_i][from_j]:
        return False
    if not checkValidPieceMove(from_i, from_j, i, j):
        print("Invalid Move. Try Again")
        return False
    return True

def findingSquares(diff):
    to_i = None
    to_j = None
    from_i = None
    from_j = None

    count = 0
    toRemove = []
    toMove = ''
    if (curr_board_state.toMove):
        toMove = "White"
    else:
        toMove = "Black"
    if(len(diff) == 3):
        for diffSquare in diff:
            countEnPassant = 0
            for i in range(8):
                for j in range(8):
                    if(diffSquare == countEnPassant 
                       and curr_board_state.arr[i][j].name
                       and curr_board_state.arr[i][j].side != toMove):
                        toRemove.append(diffSquare)
                        break
                    else:
                        countEnPassant += 1
    for item in toRemove:
        if item in diff:
            diff.remove(item)
    toMove = None
    if (curr_board_state.toMove):
        toMove = "White"
    else:
        toMove = "Black"
    for i in range(8):
        for j in range(8): 
            found = False
            if (count == diff[0]):
                if (prev_board_state.arr[i][j].name and
                    curr_board_state.arr[i][j].side == toMove):
                    from_i, from_j = i, j
                    found = True
                    break
                else:
                    to_i, to_j = i, j
                    found = True
                    break
            else:
                count += 1
        if (found):
            break
    count = 0
    for i in range(8):
        for j in range(8): 
            found = False
            if (count == diff[1]):
                if(prev_board_state.arr[i][j].name 
                   and curr_board_state.arr[i][j].side == toMove):
                    from_i, from_j = i, j
                    found = True
                    break
                else:
                    to_i, to_j = i, j
                    found = True
                    break
            else:
                count += 1
        if (found):
            break
    return from_i, from_j, to_i, to_j

def checkValidPieceMove(from_i, from_j, i, j):
    if (curr_board_state.arr[from_i][from_j].side == "White" and
        curr_board_state.arr[from_i][from_j].name == "Pawn" and 
        (i, j) in validWhitePawnMoves(from_i, from_j)):
        return True
    if(curr_board_state.arr[from_i][from_j].side == "Black" and
        curr_board_state.arr[from_i][from_j].name == "Pawn" and 
        (i, j) in validBlackPawnMoves(from_i, from_j)):
        return True
    if(curr_board_state.arr[from_i][from_j].name == "Knight" and
        (i, j) in validKnightMoves(from_i, from_j)):
        return True
    if(curr_board_state.arr[from_i][from_j].name == "Bishop" and
        (i, j) in validBishopMoves(from_i, from_j)):
        return True
    if(curr_board_state.arr[from_i][from_j].name == "Rook" and
        (i, j) in validRookMoves(from_i, from_j)):
        return True
    if(curr_board_state.arr[from_i][from_j].name == "Queen" and
        (i, j) in validRookMoves(from_i, from_j) or 
        (i, j) in validBishopMoves(from_i, from_j)):
        return True
    if(curr_board_state.arr[from_i][from_j].name == "King" and
        (i, j) in validKingMoves(from_i, from_j)):
        return True
    return False



def convertMoveDataIntoArrayInput(move_data):
    from_i = int(move_data[1]) - 1
    from_j = letterToNumber(move_data[0])
    i = int(move_data[3]) - 1
    j = letterToNumber(move_data[2])
    return from_i, from_j, i, j

def letterToNumber(letter):
    return ord(letter.lower()) - ord('a')


async def checkAndUpdateState(data, client):
    global prev_board_state, curr_board_state, liftedPieceHexRep
    boardstate_hex_str = f"{data:016x}"
    prev_bin = bin(int(curr_board_state.hex_rep, 16))[2:].zfill(64)
    curr_bin = bin(int(boardstate_hex_str, 16))[2:].zfill(64)
    diff = [i for i in range(64) if prev_bin[i] != curr_bin[i]] 
    count_ones_prev = prev_bin.count('1')
    count_ones_curr = curr_bin.count('1')
    capture = False
    captureAndDiff = []
    # If the input hex is the same as the current board state the state has not changed
    if (boardstate_hex_str == curr_board_state.hex_rep):
        return True
    # If there is more 1's in the previous board state then a piece must have been lifted 
    if (count_ones_prev - count_ones_curr == 1):
        if (curr_board_state.mode != "Hard"):
            lightUpLEDs(diff, client)
            print("here1")
            await transmitLED(client)
        liftedPieceHexRep = boardstate_hex_str
        return True
    if (count_ones_prev - count_ones_curr == 2):
        data = await findData(boardstate_hex_str, client)
        if(data == curr_board_state.hex_rep):
            return True
        else:
            prev_bin = bin(int(curr_board_state.hex_rep, 16))[2:].zfill(64)
            input_bin = bin(int(boardstate_hex_str, 16))[2:].zfill(64)
            curr_bin = bin(int(data, 16))[2:].zfill(64)
            diff = [i for i in range(64) if prev_bin[i] != curr_bin[i]]
            diff += [i for i in range(64) if input_bin[i] != curr_bin[i]]
            diff = removeDuplicates(diff)
            capture = True

    
    captureAndDiff.append(capture)
    captureAndDiff.append(diff)
    # Check the validity of the move
    if not checkValidMove(diff):
        return False
    prev_board_state.hex_rep = curr_board_state.hex_rep
    prev_board_state.toMove = curr_board_state.toMove
    prev_board_state.arr = copy.deepcopy(curr_board_state.arr)
    #prev_board_state.hex_rep = curr_board_state.hex_rep 

    curr_board_state.toMove = BLACK if curr_board_state.toMove else WHITE
    
    if (capture):
        curr_board_state.hex_rep = data
    else:
        curr_board_state.hex_rep = boardstate_hex_str
    updateboardstate(prev_board_state.hex_rep, curr_board_state.hex_rep, 
                     curr_board_state.toMove, captureAndDiff)
    
async def findData(curr_hex, client):
    while 1:
        try:
            data_from_controller = await client.read_gatt_char(BOARD_STATE_UUID)
            data_decoded = data_from_controller.decode('utf-8')
            data = int(data_decoded)
            data_hex = f"{data:016x}"
            if data_hex != curr_hex:
                return data_hex
        except Exception as e:
            print(f"[findData] BLE read error: {e}")
        await asyncio.sleep(0.2)
        

def removeDuplicates(diff):
    seen = set()
    no_duplicates = []
    for item in diff:
        if item not in seen:
            seen.add(item)
            no_duplicates.append(item)
    return no_duplicates

def removeCapturedPiece(diff):
    if (len(diff) != 3):
        return diff
    toRemove = []
    toMove = ''
    if (curr_board_state.toMove):
        toMove = 'White'
    else:
        toMove = 'Black'
    for diffSquare in diff:
        countEnPassant = 0
        for i in range(8):
            for j in range(8):
                curr_board_state.arr[i][j].side
                if(diffSquare == countEnPassant
                       and curr_board_state.arr[i][j].name
                       and curr_board_state.arr[i][j].side != toMove):
                    toRemove.append(diffSquare)
                    break
                else:
                    countEnPassant += 1
    for item in toRemove:
        if item in diff:
            diff.remove(item)
    return diff
            
def updateboardstate(prev_hex, curr_hex, curr_toMove, captureAndDiff):   
    global prev_board_state, curr_board_state,movesInGame
    global halfMovesSinceCaptureOrPawnMove, enPassantMovesAvailable
    prev_bin = bin(int(prev_hex, 16))[2:].zfill(64)
    curr_bin = bin(int(curr_hex, 16))[2:].zfill(64)
    if (captureAndDiff[0]):
        diff = captureAndDiff[1]
    else:
        diff = [i for i in range(64) if prev_bin[i] != curr_bin[i]]
    apply_piece_change(diff)    

    if (curr_board_state.toMove == WHITE):
        movesInGame += 1

    if determiningCaptureOrPawnMove(diff):
        halfMovesSinceCaptureOrPawnMove = 0
    else:
        halfMovesSinceCaptureOrPawnMove += 1

    enPassantMovesAvailable.clear()

    enPassantMoves = enPassantAvailable(diff)

    if not len(enPassantMoves) == 0:
        enPassantMovesAvailable = enPassantMoves


    fen = convertArrayToFenString(curr_board_state.arr, curr_board_state.toMove)

    curr_board_state = BoardState(curr_hex, curr_board_state.arr, curr_toMove, fen, None, curr_board_state.mode)
    return curr_board_state.arr

def enPassantAvailable(diff):
    enPassantAvailableArray = []
    piecesInMove = findPiecesInMove(diff)
    if(piecesInMove[0][0].name == "Pawn" and not piecesInMove[1][0].name and
       abs(piecesInMove[0][1] - piecesInMove[1][1]) == 2):
        if (piecesInMove[0][0].side == "White"):
            enPassantAvailableArray.append((piecesInMove[0][1] + 1, piecesInMove[1][2]))
        else:
            enPassantAvailableArray.append((piecesInMove[0][1] - 1, piecesInMove[1][2]))
    elif(piecesInMove[1][0].name == "Pawn" and not piecesInMove[0][0].name and
        abs(piecesInMove[0][1] - piecesInMove[1][1]) == 2):
        if (piecesInMove[1][0].side == "White"):
            enPassantAvailableArray.append((piecesInMove[1][1] + 1, piecesInMove[0][2]))
        else:
            enPassantAvailableArray.append((piecesInMove[1][1] - 1, piecesInMove[0][2]))
    return enPassantAvailableArray  

def determiningCaptureOrPawnMove(diff):
    piecesInMove = findPiecesInMove(diff)
    if(piecesInMove[0][0].name and piecesInMove[1][0].name):
        return True
    if(piecesInMove[0][0].name == "Pawn" 
       or piecesInMove[1][0].name == "Pawn"):
        return True
    return False

def apply_piece_change(diff): 
    global prev_board_state, curr_board_state
    if (castle(diff)):
        return
    piecesInMove = findPiecesInMove(diff)
    # Capturing a piece
    if (piecesInMove[0][0].name and piecesInMove[1][0].name):
        if(piecesInMove[0][0].side == prev_board_state.toMove):
            from_i, from_j = piecesInMove[0][1], piecesInMove[0][2]
            to_i, to_j = piecesInMove[1][1], piecesInMove[1][2]
            curr_board_state.arr[to_i][to_j] = piecesInMove[0][0]
            curr_board_state.arr[from_i][from_j] = blank_square
            removeCastling(piecesInMove)
        else:
            from_i, from_j = piecesInMove[1][1], piecesInMove[1][2]
            to_i, to_j = piecesInMove[0][1], piecesInMove[0][2]
            curr_board_state.arr[to_i][to_j] = piecesInMove[1][0]
            curr_board_state.arr[from_i][from_j] = blank_square 
            removeCastling(piecesInMove)
    # Moving without capture and en-passant capture
    positiveOrNegative = 0
    if(piecesInMove[0][0].side == "White"):
        positiveOrNegative -= 1
    else:
        positiveOrNegative += 1
    if (piecesInMove[0][0].name):
        from_i, from_j = piecesInMove[0][1], piecesInMove[0][2]
        to_i, to_j = piecesInMove[1][1], piecesInMove[1][2]
        curr_board_state.arr[to_i][to_j] = piecesInMove[0][0]
        curr_board_state.arr[from_i][from_j] = blank_square
        removeCastling(piecesInMove)
        if(len(enPassantMovesAvailable) == 0):
            return
        elif(enPassantMovesAvailable[0][0] == to_i
         and enPassantMovesAvailable[0][1] == to_j):
            curr_board_state.arr[to_i + positiveOrNegative][to_j] = blank_square
    else:
        from_i, from_j = piecesInMove[1][1], piecesInMove[1][2]
        to_i, to_j = piecesInMove[0][1], piecesInMove[0][2]
        curr_board_state.arr[to_i][to_j] = piecesInMove[1][0]
        curr_board_state.arr[from_i][from_j] = blank_square
        removeCastling(piecesInMove) 
        if(len(enPassantMovesAvailable) == 0):
            return
        elif(enPassantMovesAvailable[0][0] == to_i
         and enPassantMovesAvailable[0][1] == to_j):
            curr_board_state.arr[to_i + positiveOrNegative][to_j] = blank_square

def castle(diff):
    if all(x in diff for x in [4, 5, 6, 7]):
        curr_board_state.arr[0][6] = prev_board_state.arr[0][4]
        curr_board_state.arr[0][5] = prev_board_state.arr[0][7]
        curr_board_state.arr[0][4] = blank_square
        curr_board_state.arr[0][7] = blank_square
        whiteCastlingAvailable.clear()
        return True
    if all(x in diff for x in [1, 3, 4, 5]):
        curr_board_state.arr[0][1] = prev_board_state.arr[0][4]
        curr_board_state.arr[0][2] = prev_board_state.arr[0][0]
        curr_board_state.arr[0][0] = blank_square
        curr_board_state.arr[0][4] = blank_square
        whiteCastlingAvailable.clear()
        return True
    if all(x in diff for x in [60, 61, 62, 63]):
        curr_board_state.arr[7][6] = prev_board_state.arr[7][4]
        curr_board_state.arr[7][5] = prev_board_state.arr[7][7]
        curr_board_state.arr[7][7] = blank_square
        curr_board_state.arr[7][4] = blank_square
        blackCastlingAvailable.clear()
        return True
    if all(x in diff for x in [57, 59, 60, 61]):
        curr_board_state.arr[7][1] = prev_board_state.arr[7][4]
        curr_board_state.arr[7][2] = prev_board_state.arr[7][0]
        curr_board_state.arr[7][0] = blank_square
        curr_board_state.arr[7][4] = blank_square
        blackCastlingAvailable.clear()
        return True
    return False

def removeCastling(piecesInMove):
    count = 0
    toMove = ''
    if (prev_board_state.toMove):
        toMove = "White"
    else:
        toMove = "Black"
    piece = None
    j = None
    for pieces in piecesInMove:
        if (piecesInMove[count][0].name and piecesInMove[count][0].side == toMove):
            piece, j = pieces[0], pieces[2]
            break
        else:
            count += 1
    if(piece == None):
        return
    if (piece.name == "King" and piece.side == "White"):
        whiteCastlingAvailable.clear()
    if (piece.name == "King" and piece.side == "Black"):
        blackCastlingAvailable.clear()
    if (piece.name == "Rook" and piece.side == "White"):
        if (j == 0  and 'Q' in whiteCastlingAvailable):
            whiteCastlingAvailable.remove('Q')
        elif (j == 7 and 'K' in whiteCastlingAvailable):
           whiteCastlingAvailable.remove('K')
    if (piece.name == "Rook" and piece.side == "Black"):
        if (j == 0  and 'q' in blackCastlingAvailable):
            blackCastlingAvailable.remove('q')
        elif (j == 7 and 'k' in blackCastlingAvailable):
            blackCastlingAvailable.remove('k')

def findPiecesInMove(diff):
    count = 0
    piecesInMove = []
    for i in range(8):
        found = False
        for j in range(8):
            if(count == diff[0]): 
                piecesInMove.append((prev_board_state.arr[i][j], i, j))
                found = True
                break
            else:
                count += 1
        if (found):
            break
    count = 0
    for i in range(8):
        found = False
        for j in range(8):
            if(count == diff[1]):   
                piecesInMove.append((prev_board_state.arr[i][j], i, j))
                found = True
                break
            else:
                count += 1
        if (found):
            break
    return piecesInMove
def init_board():
    global prev_board_state, curr_board_state
    # Create Board Class
    #Initialise the pieces
    white_king = Piece("King", "White")
    white_queen = Piece("Queen", "White")
    white_rook = Piece("Rook", "White")
    white_knight = Piece("Knight", "White")
    white_bishop = Piece("Bishop", "White")
    white_pawn = Piece ("Pawn", "White")
    black_king = Piece("King", "Black")
    black_queen = Piece("Queen", "Black")
    black_rook = Piece("Rook", "Black")
    black_knight = Piece("Knight", "Black")
    black_bishop = Piece("Bishop", "Black")
    black_pawn = Piece ("Pawn", "Black")

    # Initialise board
    rows, cols = (8,8)
    board_arr = [[blank_square for _ in range(cols)] for _ in range(rows)]
    for i in range(8):
        board_arr[1][7 - i] = white_pawn
        board_arr[6][7 - i] = black_pawn

# White pieces on row 0
    board_arr[0][7] = white_rook
    board_arr[0][6] = white_knight
    board_arr[0][5] = white_bishop
    board_arr[0][4] = white_king
    board_arr[0][3] = white_queen
    board_arr[0][2] = white_bishop
    board_arr[0][1] = white_knight
    board_arr[0][0] = white_rook

# Black pieces on row 7
    board_arr[7][7] = black_rook
    board_arr[7][6] = black_knight
    board_arr[7][5] = black_bishop
    board_arr[7][4] = black_king
    board_arr[7][3] = black_queen
    board_arr[7][2] = black_bishop
    board_arr[7][1] = black_knight
    board_arr[7][0] = black_rook

    # Create previous and current board states
    fen = convertArrayToFenString(board_arr, WHITE)

    while 1:
    
        modeInput = input(
        "Select difficulty?\n"
        "Reply 'e' for easy, 'm' for medium, 'h' for hard: "
        )

        if(modeInput == 'e'):
            mode = "Easy"
            break
        elif(modeInput == 'm'):
            mode = "Medium"
            break
        elif(modeInput == 'h'):
            mode = "Hard"
            break
        else:
            print("Invalid input. Try again!")


    prev_board_state = BoardState("ffff00000000ffff", board_arr, WHITE, fen , computerSide, mode )
    curr_board_state = BoardState("ffff00000000ffff", board_arr, WHITE, fen , computerSide, mode)

    return board_arr

def convertArrayToFenString(arr, toMove):
    # Board Representation
    fen = ""
    for i in range(7, -1, -1):
        count = 0
        for j in range(8):
            if (arr[i][j].name):
                if (count > 0):
                    fen += str(count)
                if (arr[i][j].name == "Knight"):
                    abbrev = arr[i][j].name[1]
                else:
                    abbrev = arr[i][j].name[0]                
                fen += abbrev.upper() if arr[i][j].side == "White" else abbrev.lower()
                count = 0
            else:
                count += 1 
        fen += str(count) if count > 0 else '' 
        if (i != 0):
            fen += '/'     
    # To Move  
    fen += ' ' 
    fen += 'w' if toMove else 'b'
    # Castling
    fen += ' '
    if (len(whiteCastlingAvailable) == 0 and len(blackCastlingAvailable) == 0):
        fen += '-'
        fen += ' '
    # White Castling
    whiteCastlingString = ''
    if (len(whiteCastlingAvailable) != 0):
        for castlingOption in whiteCastlingAvailable:
            whiteCastlingString += castlingOption
        fen += whiteCastlingString
    # Black Castling
    blackCastlingString = ''
    if (len(blackCastlingAvailable) != 0):
        for castlingOption in blackCastlingAvailable:
            blackCastlingString += castlingOption
        fen += blackCastlingString
    # Enpassant move available  
    fen += ' '
    if (len(enPassantMovesAvailable) == 0):
        fen += '-'
    else:
        for enPassantMove in enPassantMovesAvailable:
            ePi, ePj = enPassantMove
            fen += toSquare(ePi, ePj)  
    # How many moves since a capture or a pawn move
    fen += ' '
    fen += str(halfMovesSinceCaptureOrPawnMove)
    # What it the number of moves
    fen += ' '
    fen += str(movesInGame)
    return fen

def toSquare(i, j):
    file = chr(ord('a') + j)     
    rank = str(i + 1)            
    return file + rank

def print_board(board):
    for i in range(7, -1, -1):  # Start from row 7 down to 0
        row = board[i]
        row_str = ""
        for piece in row:
            if piece.name:  # If not blank
                abbrev = (piece.side[0] + piece.name[:2]).upper()
                row_str += f"{abbrev:>3} "
            else:
                row_str += " .  "
        print(row_str)

async def computerUpdateState(fen, uci, client):
    global ledData
    ledData.clear()

    input("Continue? ")

    prev_board_state.hex_rep = curr_board_state.hex_rep
    prev_board_state.toMove = curr_board_state.toMove
    prev_board_state.arr = copy.deepcopy(curr_board_state.arr)

    
    from_i, from_j, i, j = convertMoveDataIntoArrayInput(uci)
    curr_board_state.arr = fenToBoardState(fen)
    print_board(curr_board_state.arr)
    curr_board_state.hex_rep = obtainHexRep(fen)
    print(curr_board_state.hex_rep)
    curr_board_state.toMove = not prev_board_state.toMove
    curr_board_state.fen = fen

    print(f"Light up [{i}, {j}]")
    red = 255
    green = 255
    blue = 255
    print(f"Colour: White, Red: {red}, Green: {green}, Blue: {blue}")
    ledData.append(ledVal(i,j,red,blue,green))
    await transmitLED(client)
    # Wait until that piece has been put on that square
    while 1:
        try:
            data_from_controller = await client.read_gatt_char(BOARD_STATE_UUID)
            data_decoded = data_from_controller.decode('utf-8') #convert byte to str
            data = int(data_decoded)
            data_hex = f"{data:016x}"
            if data_hex == curr_board_state.hex_rep:
                return data_hex
            # Checking if data is 16 bits else Invalid Input                     

        except Exception:
            pass
# Function gets given fen string and returns a hexadecimal representation
def fenToBoardState(fen):
    board_section = fen.split(' ')[0]
    rows, cols = (8, 8)
    arr = [[blank_square for _ in range(cols)] for _ in range(rows)]
    piece_map = {
        'r': Piece("Rook", "Black"),
        'n': Piece("Knight", "Black"),
        'b': Piece("Bishop", "Black"),
        'q': Piece("Queen", "Black"),
        'k': Piece("King", "Black"),
        'p': Piece("Pawn", "Black"),
        'R': Piece("Rook", "White"),
        'N': Piece("Knight", "White"),
        'B': Piece("Bishop", "White"),
        'Q': Piece("Queen", "White"),
        'K': Piece("King", "White"),
        'P': Piece("Pawn", "White")
    }

    fen_rows = board_section.split('/')
    for fen_row_index, fen_row in enumerate(fen_rows):
        i = 7 - fen_row_index  # Flip row index so FEN's top row becomes bottom in array
        j = 0
        for c in fen_row:
            if c.isdigit():
                j += int(c)
            elif c in piece_map:
                arr[i][j] = piece_map[c]
                j += 1
    return arr    
    
def obtainHexRep(fen):

    board_section = fen.split(' ')[0]
    rows = board_section.split('/')
    bitstring = ""
    rows = rows[::-1]
    for row in rows:
        row_bits = ""
        for char in row:
            if char.isdigit():
                row_bits += '0' * int(char)
            elif char in "rnbqkpRNBQKP":
                row_bits += '1'
            else:
                raise ValueError(f"Invalid FEN character: {char}")
        bitstring += row_bits

    if len(bitstring) != 64:
        raise ValueError(f"Generated bitstring is not 64 bits: {len(bitstring)} bits")

    # Convert binary string to hex
    return f"{int(bitstring, 2):016x}"
   
# Light Up LEDs function
def lightUpLEDs(diff, client):
    count = 0
    for i in range(8):
        for j in range(8):
            if(count == diff[0]): 
                lightLEDSquares(curr_board_state.arr[i][j].side, 
                               curr_board_state.arr[i][j].name, i, j, client)
                return
            count += 1    
    return False

def lightLEDSquares(side, piece, i, j, client):
    if (side == "White" and piece == "Pawn"):
        print("here6")
        lightLEDWhitePawn(i, j)
        print("here2")

    elif(side == "Black" and piece == "Pawn"):
        lightLEDBlackPawn(i, j)

    elif(piece == "Knight"):
        lightLEDKnight(i, j)

    elif(piece == "Bishop"):
        lightLEDBishop(i,j)
    elif(piece == "Rook"):
        lightLEDRook(i, j)
    elif(piece == "Queen"):
        lightLEDBishop(i,j)
        lightLEDRook(i,j)
    elif(piece == "King"):
        lightLEDKing(i, j)

# This part is my functions of lighting up specific pieces
# Lighting potential White Pawn Moves
def lightLEDWhitePawn(i, j):
    print("here5")
    global ledData

    l_i = None
    l_j = None
    red = None
    blue = None
    green = None
    colour = None
    if(i == 1):
        if not curr_board_state.arr[i + 1][j].name:
            colour, red, blue, green = evaluate_move(i, j, i + 1, j)
            print("Light up square" + f"[{i + 1}][{j}]")
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i+1,j,red,blue,green))
        if not curr_board_state.arr[i + 2][j].name:
            colour, red, blue, green = evaluate_move(i, j, i + 2, j)
            print("Light up square" + f"[{i + 2}][{j}]")
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i+2,j,red,blue,green))
    elif not curr_board_state.arr[i + 1][j].name and i + 1 < 7:
        print("Light up square" + f"[{i + 1}][{j}]")
        colour, red, blue, green = evaluate_move(i, j, i + 2, j)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i+1,j,red,blue,green))
    print("here11")
    if (j - 1 >= 0 and curr_board_state.arr[i + 1][j - 1].name and 
    (curr_board_state.arr[i][j].side != 
        curr_board_state.arr[i + 1][j - 1].side)):
        print("here9")   
        print("Light up square" + f"[{i + 1}][{j - 1}]")
        colour, red, blue, green = evaluate_move(i, j, i + 1, j - 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i+1,j-1,red,blue,green))
    if (j + 1 <= 7 and curr_board_state.arr[i + 1][j + 1].name and 
    (curr_board_state.arr[i][j].side != 
        curr_board_state.arr[i + 1][j + 1].side)):
        print("here10")
        print("Light up square" + f"[{i + 1}][{j + 1}]")
        colour, red, blue, green = evaluate_move(i, j, i + 1, j + 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i+1,j+1,red,blue,green))
        print("here7")
    count = 0
    found = False
    square = ''
    for char in curr_board_state.fen:
        if (found):
            square += char
            l_i, l_j = findSquaresFromElement(square)
            break
        if (count == FENSPACESFOREP):
            if (char == '-'):
                return
            found = True
            square += char
        if (char == ' '):
            count += 1
    if (l_i == None or l_j == None):
        return
    if ((l_i == i + 1) and (l_j == j + 1)):
        print("Light up square" + f" [{i + 1}][{j + 1}]")
        colour, red, blue, green = evaluate_move(i, j, i + 1, j + 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i+1,j+1,red,blue,green))
    elif ((l_i == i + 1) and (l_j == j - 1)):
        print("Light up square" + f" [{i + 1}][{j - 1}]")
        colour, red, blue, green = evaluate_move(i, j, i + 1, j - 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i+1,j-1,red,blue,green))


def lightLEDBlackPawn(i, j):
    global ledData

    l_i = None
    l_j = None
    if(i == 6):
        if not curr_board_state.arr[i - 1][j].name:
            print("Light up square" + f"[{i - 1}][{j}]")
            colour, red, blue, green = evaluate_move(i, j, i - 1, j)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i-1,j,red,blue,green))
        if not curr_board_state.arr[i - 2][j].name:
            print("Light up square" + f"[{i - 2}][{j}]")
            colour, red, blue, green = evaluate_move(i, j, i - 2, j)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i-2,j,red,blue,green))
    elif not curr_board_state.arr[i - 1][j].name and i + 1 < 7:
            print("Light up square" + f"[{i - 1}][{j}]")
            colour, red, blue, green = evaluate_move(i, j, i - 1, j)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i-1,j,red,blue,green))
    if (j - 1 >= 0 and curr_board_state.arr[i - 1][j - 1].name and 
    (curr_board_state.arr[i][j].side != 
        curr_board_state.arr[i - 1][j - 1].side)):   
        print("Light up square" + f"[{i - 1}][{j - 1}]")
        colour, red, blue, green = evaluate_move(i, j, i - 1, j - 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i-1,j-1,red,blue,green))
    if (j + 1 <= 7 and curr_board_state.arr[i - 1][j + 1].name and 
    (curr_board_state.arr[i][j].side != 
        curr_board_state.arr[i - 1][j + 1].side)):
        print("Light up square" + f"[{i - 1}][{j + 1}]")
        colour, red, blue, green = evaluate_move(i, j, i - 1, j + 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i-1,j+1,red,blue,green))
    count = 0
    found = False
    square = ''
    for char in curr_board_state.fen:
        if (found):
            square += char
            l_i, l_j = findSquaresFromElement(square)
            break
        if (count == FENSPACESFOREP):
            if (char == '-'):
                return
            found = True
            square += char
        if (char == ' '):
            count += 1
    if (l_i == None or l_j == None):
        return
    if ((l_i == i - 1) and (l_j == j + 1)):
        print("Light up square" + f" [{i - 1}][{j + 1}]")
        colour, red, blue, green = evaluate_move(i, j, i - 1, j + 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i-1,j+1,red,blue,green))
    elif ((l_i == i - 1) and (l_j == j - 1)):
        print("Light up square" + f" [{i - 1}][{j - 1}]")
        colour, red, blue, green = evaluate_move(i, j, i - 1, j - 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i-1,j-1,red,blue,green))

def findSquaresFromElement(str):
    file = str[0]
    rank = str[1]
    j = ord(file) - ord('a')  # column
    i = int(rank) - 1         # row
    return (i, j)
    
def lightLEDKnight(i, j):
    global ledData

    if (not (i - 1 < 0 or j - 2 < 0) and 
        curr_board_state.arr[i - 1][j - 2].side != curr_board_state.arr[i][j].side):
        print(f"Light up square [{i - 1}][{j - 2}]")
        colour, red, blue, green = evaluate_move(i, j, i - 1, j - 2)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i - 1, j - 2, red, blue, green))
    if (not (i - 2 < 0 or j - 1 < 0) and 
        curr_board_state.arr[i - 2][j - 1].side != curr_board_state.arr[i][j].side):
        print(f"Light up square [{i - 2}][{j - 1}]")
        colour, red, blue, green = evaluate_move(i, j, i - 2, j - 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i - 2, j - 1, red, blue, green))
    if (not (i - 2 < 0 or j + 1 > 7) and 
        curr_board_state.arr[i - 2][j + 1].side != curr_board_state.arr[i][j].side):
        print(f"Light up square [{i - 2}][{j + 1}]")
        colour, red, blue, green = evaluate_move(i, j, i - 2, j + 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i - 2, j + 1, red, blue, green))
    if (not (i - 1 < 0 or j + 2 > 7) and 
        curr_board_state.arr[i - 1][j + 2].side != curr_board_state.arr[i][j].side):
        print(f"Light up square [{i - 1}][{j + 2}]")
        colour, red, blue, green = evaluate_move(i, j, i - 1, j + 2)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i - 1, j + 2, red, blue, green))
    if (not (i + 1 > 7 or j + 2 > 7) and 
        curr_board_state.arr[i + 1][j + 2].side != curr_board_state.arr[i][j].side):
        print(f"Light up square [{i + 1}][{j + 2}]")
        colour, red, blue, green = evaluate_move(i, j, i + 1, j + 2)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i + 1, j + 2, red, blue, green))
    if (not (i + 2 > 7 or j + 1 > 7) and 
        curr_board_state.arr[i + 2][j + 1].side != curr_board_state.arr[i][j].side):
        print(f"Light up square [{i + 2}][{j + 1}]")
        colour, red, blue, green = evaluate_move(i, j, i + 2, j + 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i + 2, j + 1, red, blue, green))
    if (not (i + 2 > 7 or j - 1 < 0) and 
        curr_board_state.arr[i + 2][j - 1].side != curr_board_state.arr[i][j].side):
        print(f"Light up square [{i + 2}][{j - 1}]")
        colour, red, blue, green = evaluate_move(i, j, i + 2, j - 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i + 2, j - 1, red, blue, green))
    if (not (i + 1 > 7 or j - 2 < 0) and 
        curr_board_state.arr[i + 1][j - 2].side != curr_board_state.arr[i][j].side):
        print(f"Light up square [{i + 1}][{j - 2}]")
        colour, red, blue, green = evaluate_move(i, j, i + 1, j - 2)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i + 1, j - 2, red, blue, green))

def lightLEDBishop(i, j):
    global ledData

    n = 1
    while (i + n <= 7 and j - n >= 0):
        if (curr_board_state.arr[i + n][j - n].name):
            if (curr_board_state.arr[i][j].side != curr_board_state.arr[i + n][j - n].side):
                print(f"Light up square [{i + n}][{j - n}]")
                colour, red, blue, green = evaluate_move(i, j, i + n, j - n)
                print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
                ledData.append(ledVal(i + n, j - n, red, blue, green))
            break
        else:
            print(f"Light up square [{i + n}][{j - n}]")
            colour, red, blue, green = evaluate_move(i, j, i + n, j - n)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i + n, j - n, red, blue, green))
            n += 1

    n = 1
    while (i + n <= 7 and j + n <= 7):
        if (curr_board_state.arr[i + n][j + n].name):
            if (curr_board_state.arr[i][j].side != curr_board_state.arr[i + n][j + n].side):
                print(f"Light up square [{i + n}][{j + n}]")
                colour, red, blue, green = evaluate_move(i, j, i + n, j + n)
                print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
                ledData.append(ledVal(i + n, j + n, red, blue, green))
            break
        else:
            print(f"Light up square [{i + n}][{j + n}]")
            colour, red, blue, green = evaluate_move(i, j, i + n, j + n)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i + n, j + n, red, blue, green))
            n += 1

    n = 1
    while (i - n >= 0 and j - n >= 0):
        if (curr_board_state.arr[i - n][j - n].name):
            if (curr_board_state.arr[i][j].side != curr_board_state.arr[i - n][j - n].side):
                print(f"Light up square [{i - n}][{j - n}]")
                colour, red, blue, green = evaluate_move(i, j, i - n, j - n)
                print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
                ledData.append(ledVal(i - n, j - n, red, blue, green))
            break
        else:
            print(f"Light up square [{i - n}][{j - n}]")
            colour, red, blue, green = evaluate_move(i, j, i - n, j - n)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i - n, j - n, red, blue, green))
            n += 1

    n = 1
    while (i - n >= 0 and j + n <= 7):
        if (curr_board_state.arr[i - n][j + n].name):
            if (curr_board_state.arr[i][j].side != curr_board_state.arr[i - n][j + n].side):
                print(f"Light up square [{i - n}][{j + n}]")
                colour, red, blue, green = evaluate_move(i, j, i - n, j + n)
                print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
                ledData.append(ledVal(i - n, j + n, red, blue, green))
            break
        else:
            print(f"Light up square [{i - n}][{j + n}]")
            colour, red, blue, green = evaluate_move(i, j, i - n, j + n)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i - n, j + n, red, blue, green))
            n += 1

def lightLEDRook(i, j):
    global ledData

    n = 1
    while (i + n <= 7):
        if (curr_board_state.arr[i + n][j].name):
            if (curr_board_state.arr[i][j].side != curr_board_state.arr[i + n][j].side):
                print(f"Light up square [{i + n}][{j}]")
                colour, red, blue, green = evaluate_move(i, j, i + n, j)
                print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
                ledData.append(ledVal(i + n, j, red, blue, green))
            break
        else:
            print(f"Light up square [{i + n}][{j}]")
            colour, red, blue, green = evaluate_move(i, j, i + n, j)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i + n, j, red, blue, green))
            n += 1

    n = 1
    while (i - n >= 0):
        if (curr_board_state.arr[i - n][j].name):
            if (curr_board_state.arr[i][j].side != curr_board_state.arr[i - n][j].side):
                print(f"Light up square [{i - n}][{j}]")
                colour, red, blue, green = evaluate_move(i, j, i - n, j)
                print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
                ledData.append(ledVal(i - n, j, red, blue, green))
            break
        else:
            print(f"Light up square [{i - n}][{j}]")
            colour, red, blue, green = evaluate_move(i, j, i - n, j)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i - n, j, red, blue, green))
            n += 1

    n = 1
    while (j - n >= 0):
        if (curr_board_state.arr[i][j - n].name):
            if (curr_board_state.arr[i][j].side != curr_board_state.arr[i][j - n].side):
                print(f"Light up square [{i}][{j - n}]")
                colour, red, blue, green = evaluate_move(i, j, i, j - n)
                print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
                ledData.append(ledVal(i, j - n, red, blue, green))
            break
        else:
            print(f"Light up square [{i}][{j - n}]")
            colour, red, blue, green = evaluate_move(i, j, i, j - n)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i, j - n, red, blue, green))
            n += 1

    n = 1
    while (j + n <= 7):
        if (curr_board_state.arr[i][j + n].name):
            if (curr_board_state.arr[i][j].side != curr_board_state.arr[i][j + n].side):
                print(f"Light up square [{i}][{j + n}]")
                colour, red, blue, green = evaluate_move(i, j, i, j + n)
                print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
                ledData.append(ledVal(i, j + n, red, blue, green))
            break
        else:
            print(f"Light up square [{i}][{j + n}]")
            colour, red, blue, green = evaluate_move(i, j, i, j + n)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i, j + n, red, blue, green))
            n += 1


def lightLEDKing(i, j): 
    global ledData

    if (i - 1 >= 0 and (not curr_board_state.arr[i - 1][j].name or 
        curr_board_state.arr[i][j].side != curr_board_state.arr[i - 1][j].side)):
        print("Light up square" + f"[{i - 1}][{j}]")
        colour, red, blue, green = evaluate_move(i, j, i - 1, j)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i - 1, j, red, blue, green))

    if (i + 1 <= 7 and (not curr_board_state.arr[i + 1][j].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i + 1][j].side)):
        print("Light up square" + f"[{i + 1}][{j}]")
        colour, red, blue, green = evaluate_move(i, j, i + 1, j)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i + 1, j, red, blue, green))

    if (j - 1 >= 0 and (not curr_board_state.arr[i][j - 1].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i][j - 1].side)):
        print("Light up square" + f"[{i}][{j - 1}]")
        colour, red, blue, green = evaluate_move(i, j, i, j - 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i, j - 1, red, blue, green))

    if (j + 1 <= 7 and 
        (not curr_board_state.arr[i][j + 1].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i][j + 1].side)):
        print("Light up square" + f"[{i}][{j + 1}]")
        colour, red, blue, green = evaluate_move(i, j, i, j + 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i, j + 1, red, blue, green))

    if (i - 1 >= 0 and j - 1 >= 0 and 
        (not curr_board_state.arr[i - 1][j - 1].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i - 1][j - 1].side)):
        print("Light up square" + f"[{i - 1}][{j - 1}]")
        colour, red, blue, green = evaluate_move(i, j, i - 1, j - 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i - 1, j - 1, red, blue, green))

    if (i - 1 >= 0 and j + 1 <= 7 and
        (not curr_board_state.arr[i - 1][j + 1].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i - 1][j + 1].side)):
        print("Light up square" + f"[{i - 1}][{j + 1}]")
        colour, red, blue, green = evaluate_move(i, j, i - 1, j + 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i - 1, j + 1, red, blue, green))

    if (i + 1 <= 7 and j - 1 >= 0 and 
        (not curr_board_state.arr[i + 1][j - 1].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i + 1][j - 1].side)):
        print("Light up square" + f"[{i + 1}][{j - 1}]")
        colour, red, blue, green = evaluate_move(i, j, i + 1, j - 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i + 1, j - 1, red, blue, green))

    if (i + 1 <= 7 and j + 1 <= 7 and 
        (not curr_board_state.arr[i + 1][j + 1].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i + 1][j + 1].side)):
        print("Light up square" + f"[{i + 1}][{j + 1}]")
        colour, red, blue, green = evaluate_move(i, j, i + 1, j + 1)
        print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
        ledData.append(ledVal(i + 1, j + 1, red, blue, green))

    # Long Castle / Queen side Castling
    if (
        j - 3 >= 0 and
        not curr_board_state.arr[i][j - 1].name and
        not curr_board_state.arr[i][j - 2].name and
        not curr_board_state.arr[i][j - 3].name
    ):
        if curr_board_state.arr[i][j].side == "White" and 'Q' in whiteCastlingAvailable:
            print(f"Light up square [{i}][{j - 2}]")
            colour, red, blue, green = evaluate_move(i, j, i, j - 2)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i, j - 2, red, blue, green))
        elif curr_board_state.arr[i][j].side == "Black" and 'q' in blackCastlingAvailable:
            print(f"Light up square [{i}][{j - 2}]")
            colour, red, blue, green = evaluate_move(i, j, i, j - 2)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i, j - 2, red, blue, green))

    # Short Castle / King side Castling
    if (
        j + 2 <= 7 and
        not curr_board_state.arr[i][j + 1].name and
        not curr_board_state.arr[i][j + 2].name
    ):
        if curr_board_state.arr[i][j].side == "White" and 'K' in whiteCastlingAvailable:
            print(f"Light up LEDs: [{i}][{j + 2}]")
            colour, red, blue, green = evaluate_move(i, j, i, j + 2)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i, j + 2, red, blue, green))
        elif curr_board_state.arr[i][j].side == "Black" and 'k' in blackCastlingAvailable:
            print(f"Light up LEDs: [{i}][{j + 2}]")
            colour, red, blue, green = evaluate_move(i, j, i, j + 2)
            print(f"Colour: {colour}, Red: {red}, Green: {green}, Blue: {blue}")
            ledData.append(ledVal(i, j + 2, red, blue, green))
         
# This section evaluates what valid moves that a particular piece can move
# This function finds the valid White Pawn Moves Available
def validWhitePawnMoves(i, j):
    l_i = None
    l_j = None
    validWhitePawnMoves = []
    if(i == 1):
        if not curr_board_state.arr[i + 1][j].name:
            validWhitePawnMoves.append((i + 1, j))
        if not curr_board_state.arr[i + 2][j].name:
            validWhitePawnMoves.append((i + 2, j))
    elif not curr_board_state.arr[i + 1][j].name and i + 1 < 8:
        validWhitePawnMoves.append((i + 1, j))
    if (j - 1 >= 0 and curr_board_state.arr[i + 1][j - 1].name and 
    (curr_board_state.arr[i][j].side != 
        curr_board_state.arr[i + 1][j - 1].side)):   
        validWhitePawnMoves.append((i + 1, j - 1))
    if (j + 1 <= 7 and curr_board_state.arr[i + 1][j + 1].name and 
    (curr_board_state.arr[i][j].side != 
        curr_board_state.arr[i + 1][j + 1].side)):
        validWhitePawnMoves.append((i + 1, j + 1))
        count = 0
        found = False
        square = ''
        for char in curr_board_state.fen:
            if (found):
                square += char
                l_i, l_j = findSquaresFromElement(square)
                break
            if (count == FENSPACESFOREP):
                if (char == '-'):
                    return validWhitePawnMoves
                found = True
                square += char
            if (char == ' '):
                count += 1
    if (l_i == None or l_j == None):
        return validWhitePawnMoves
    if ((l_i == i + 1) and (l_j == j + 1)):
        validWhitePawnMoves.append((i + 1, j + 1))
    elif ((l_i == i + 1) and (l_j == j - 1)):
        validWhitePawnMoves.append((i + 1, j - 1))
    return validWhitePawnMoves

def validBlackPawnMoves(i, j):
    validBlackPawnMoves = []
    if(i == 6):
        if not curr_board_state.arr[i - 1][j].name:
           validBlackPawnMoves.append((i - 1, j))
        if not curr_board_state.arr[i - 2][j].name:
            validBlackPawnMoves.append((i - 2, j))
    elif not curr_board_state.arr[i - 1][j].name and i + 1 < 8:
            validBlackPawnMoves.append((i - 1, j))
    if (j - 1 >= 0 and curr_board_state.arr[i - 1][j - 1].name and 
    (curr_board_state.arr[i][j].side != 
        curr_board_state.arr[i - 1][j - 1].side)):   
        validBlackPawnMoves.append((i - 1, j - 1))
    if (j + 1 <= 7 and curr_board_state.arr[i - 1][j + 1].name and 
    (curr_board_state.arr[i][j].side != 
        curr_board_state.arr[i - 1][j + 1].side)):
        validBlackPawnMoves.append((i - 1, j + 1))
    count = 0
    found = False
    square = ''
    for char in curr_board_state.fen:
        if (found):
            square += char
            l_i, l_j = findSquaresFromElement(square)
            break
        if (count == FENSPACESFOREP):
            if (char == '-'):
                return validBlackPawnMoves
            found = True
            square += char
        if (char == ' '):
            count += 1
    if(l_i == None or l_j == None):
        return validBlackPawnMoves
    if ((l_i == i - 1) and (l_j == j + 1)):
        validBlackPawnMoves.append((i + 1, j + 1))
    elif ((l_i == i - 1) and (l_j == j - 1)):
        validBlackPawnMoves.append((i + 1, j - 1))
    return validBlackPawnMoves
def validKnightMoves(i, j):
    validKnightMoves = []
    if (not (i - 1 < 0 or j - 2 < 0) and 
        curr_board_state.arr[i - 1][j - 2].side 
        != curr_board_state.arr[i][j].side):
       validKnightMoves.append((i - 1, j - 2))
    if (not (i - 2 < 0 or j - 1 < 0) and 
        curr_board_state.arr[i - 2][j - 1].side 
        != curr_board_state.arr[i][j].side):
        validKnightMoves.append((i - 2, j - 1))
    if (not (i - 2 < 0 or j + 1 > 7) and 
        curr_board_state.arr[i - 2][j + 1].side 
        != curr_board_state.arr[i][j].side):
        validKnightMoves.append((i - 2, j + 1))
    if (not (i - 1 < 0 or j + 2 > 7) and
        curr_board_state.arr[i - 1][j + 2].side 
        != curr_board_state.arr[i][j].side):
        validKnightMoves.append((i - 1, j + 2))
    if (not (i + 1 > 7 or j + 2 > 7) and 
        curr_board_state.arr[i + 1][j + 2].side 
        != curr_board_state.arr[i][j].side):
        validKnightMoves.append((i + 1, j + 2))
    if (not (i + 2 > 7 or j + 1 > 7) and 
        curr_board_state.arr[i + 2][j + 1].side 
        != curr_board_state.arr[i][j].side):
        validKnightMoves.append((i + 2, j + 1))
    if (not (i + 2 > 7 or j - 1 < 0) and 
        curr_board_state.arr[i + 2][j - 1].side 
        != curr_board_state.arr[i][j].side):
        validKnightMoves.append((i + 2, j - 1))
    if (not (i + 1 > 7 or j - 2 < 0) and 
        curr_board_state.arr[i + 1][j - 2].side 
        != curr_board_state.arr[i][j].side):
        validKnightMoves.append((i + 1, j - 2))
    return validKnightMoves

def validBishopMoves(i,j):
    validBishopMoves = []
    n = 1
    while (i + n <= 7 and j - n >= 0):
        if (curr_board_state.arr[i + n][j - n].name):
            if (curr_board_state.arr[i][j].side != 
                curr_board_state.arr[i + n][j - n].side):
                validBishopMoves.append((i + n, j - n))
            break
        else:
            validBishopMoves.append((i + n, j - n))
            n += 1 
    n = 1
    while (i + n <= 7 and j + n <= 7):
        if (curr_board_state.arr[i + n][j + n].name):
            if (curr_board_state.arr[i][j].side != 
                curr_board_state.arr[i + n][j + n].side):
                validBishopMoves.append((i + n, j + n))
            break
        else:
            validBishopMoves.append((i + n, j + n))
            n += 1 
    n = 1
    while (i - n >= 0 and j - n >= 0):
        if (curr_board_state.arr[i - n][j - n].name):
            if (curr_board_state.arr[i][j].side != 
                curr_board_state.arr[i - n][j - n].side):
                validBishopMoves.append((i - n, j - n))
            break
        else:
            validBishopMoves.append((i - n, j - n))
            n += 1 
    n = 1
    while (i - n >= 0 and j + n <= 7):
        if (curr_board_state.arr[i - n][j + n].name):
            if (curr_board_state.arr[i][j].side != 
                curr_board_state.arr[i - n][j + n].side):
                validBishopMoves.append((i - n, j + n))
            break
        else:
            validBishopMoves.append((i - n, j + n))
            n += 1 
    return validBishopMoves
def validRookMoves(i, j):
    validRookMoves = []
    n = 1
    while (i + n <= 7):
        if (curr_board_state.arr[i + n][j].name):
            if (curr_board_state.arr[i][j].side != 
                curr_board_state.arr[i + n][j].side):
                validRookMoves.append((i + n, j))
            break
        else:
            validRookMoves.append((i + n, j))
            n += 1 
    n = 1
    while (i - n >= 0):
        if (curr_board_state.arr[i - n][j].name):
            if (curr_board_state.arr[i][j].side != 
                curr_board_state.arr[i - n][j].side):
                validRookMoves.append((i - n, j))
            break
        else:
            validRookMoves.append((i - n, j))
            n += 1 
    n = 1
    while (j - n >= 0):
        if (curr_board_state.arr[i][j - n].name):
            if (curr_board_state.arr[i][j].side != 
                curr_board_state.arr[i][j - n].side):
                validRookMoves.append((i, j - n))
            break
        else:
            validRookMoves.append((i, j - n))
            n += 1 
    n = 1
    while (j + n <= 7):
        if (curr_board_state.arr[i][j + n].name):
            if (curr_board_state.arr[i][j].side != 
                curr_board_state.arr[i][j + n].side):
                validRookMoves.append((i, j + n))
            break
        else:
            validRookMoves.append((i, j + n))
            n += 1 
    return validRookMoves

def validKingMoves(i, j):
    validKingMoves = []

    if i - 1 >= 0 and (
        not curr_board_state.arr[i - 1][j].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i - 1][j].side
    ):
        validKingMoves.append((i - 1, j))

    if i + 1 <= 7 and (
        not curr_board_state.arr[i + 1][j].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i + 1][j].side
    ):
        validKingMoves.append((i + 1, j))

    if j - 1 >= 0 and (
        not curr_board_state.arr[i][j - 1].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i][j - 1].side
    ):
        validKingMoves.append((i, j - 1))

    if j + 1 <= 7 and (
        not curr_board_state.arr[i][j + 1].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i][j + 1].side
    ):
        validKingMoves.append((i, j + 1))

    if i - 1 >= 0 and j - 1 >= 0 and (
        not curr_board_state.arr[i - 1][j - 1].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i - 1][j - 1].side
    ):
        validKingMoves.append((i - 1, j - 1))

    if i - 1 >= 0 and j + 1 <= 7 and (
        not curr_board_state.arr[i - 1][j + 1].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i - 1][j + 1].side
    ):
        validKingMoves.append((i - 1, j + 1))

    if i + 1 <= 7 and j - 1 >= 0 and (
        not curr_board_state.arr[i + 1][j - 1].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i + 1][j - 1].side
    ):
        validKingMoves.append((i + 1, j - 1))

    if i + 1 <= 7 and j + 1 <= 7 and (
        not curr_board_state.arr[i + 1][j + 1].name or
        curr_board_state.arr[i][j].side != curr_board_state.arr[i + 1][j + 1].side
    ):
        validKingMoves.append((i + 1, j + 1))

    # Long Castle / Queen side Castling
    if (
        j - 3 >= 0 and
        not curr_board_state.arr[i][j - 1].name and
        not curr_board_state.arr[i][j - 2].name and
        not curr_board_state.arr[i][j - 3].name
    ):
        if curr_board_state.arr[i][j].side == "White" and 'Q' in whiteCastlingAvailable:
            validKingMoves.append((i, j - 2))
        elif curr_board_state.arr[i][j].side == "Black" and 'q' in blackCastlingAvailable:
            validKingMoves.append((i, j - 2))

    # Short Castle / King side Castling
    if (
        j + 2 <= 7 and
        not curr_board_state.arr[i][j + 1].name and
        not curr_board_state.arr[i][j + 2].name
    ):
        if curr_board_state.arr[i][j].side == "White" and 'K' in whiteCastlingAvailable:
            validKingMoves.append((i, j + 2))
        elif curr_board_state.arr[i][j].side == "Black" and 'k' in blackCastlingAvailable:
            validKingMoves.append((i, j + 2))

    return validKingMoves
async def run_chessboard_simulation(client):

    # Simulate a sequence of board states as integer input (representing bitboards)
    hex_list = [
    "ffff00000000ffff",
    "fff700000000ffff",
    "fff700080000ffff",
    "fff700080000f7ff",
    "fff700080800f7ff"
    ]
    [
    "ffd700080800f7ff",
    "ffd700280800f7ff",
    "ffd700280800f7ef",
    "ffd700280800f7ef",
    "ffd700290800f7ef",
    "ffd700090800f7ef",
    "ffd700092800f7ef",
    "ffd700092800e7ef",
    "ffd700093800e7ef",
    "ffd700091800e7ef",
    "ffd700090800e7ef",
    "ffd700090810e7ef",
    "ffd700090810c7ef",
    "ffd700090800c7ef",
    "ffd700090810c7ef",
    "fbd700290810c7ef",
    "fbd700290810c7ed",
    "fbd700290814c7ed",
    "ebd700290814c7ed",
    "ebdf00290814c7ed",
    "ebdf00290814c7e9",
    "ebdf00290814cfe9",
    "ebdf0029081ccfc9",
    "e9df0029081ccfc9",
    "e9df0429081ccfc9",
    "e9df0429081ccf89",
    "e9df0429081cdf89",
    "e1df0429081cdf89",
    "e6df0429081cdf89",
    "e6df0429081cdf09",
    "e6df0429081cdf09",
    "e65f0429081cdf49",
    "e65f8429081cdf49",
    "e65f8429081cdf41",
    "e65f8429081cdf46"
]

    for inputHex in hex_list:
        input_state = int(inputHex, 16)
        await checkAndUpdateState(input_state, client)
        print_board(curr_board_state.arr)
        print(curr_board_state.fen)

        stockfish.set_fen_position(curr_board_state.fen)
        evaluation = stockfish.get_evaluation()
        if evaluation["type"] == "mate" and evaluation["value"] == 0:
            print("Checkmate! Game is over.")
            break

    while 1:
        data = input("64-bit number: ")
        input_state = int(data, 16)
        await checkAndUpdateState(input_state, client)
        print_board(curr_board_state.arr)
        print(curr_board_state.fen)


def evaluate_move(from_i, from_j, to_i, to_j):  
    print("evaluating1")
    red = None
    green = None
    blue = None
    colour = None
    if (curr_board_state.mode == "Medium"):
        red = 255
        green = 255
        blue = 255
        colour = 'White'
        return colour, red, green, blue
    uci = toSquare(from_i, from_j) + toSquare(to_i, to_j)
    stockfish.set_fen_position(curr_board_state.fen)
    if(stockfish.get_best_move() == uci):
        return "Dark Green", 0, 255, 0
    eval_before = stockfish.get_evaluation()
    stockfish.make_moves_from_current_position([uci])
    eval_after = stockfish.get_evaluation()   
    colour, red, green, blue = classifyMove(eval_before, eval_after)
    return colour, red, green, blue

def classifyMove(eval_before, eval_after):
    before = score(eval_before)
    after = score(eval_after)
    drop = before - after if (curr_board_state.toMove) else after - before
    print(drop)
    if drop < -50:
        return "Light Blue", 144, 238, 144
    elif drop < 0:
        return "Dark Blue", 0, 0, 238
    elif drop <= 50:
        return "White", 255, 255, 255
    elif drop <= 100:
        return "Yellow", 255, 255, 0
    elif drop <= 150:
        return "Orange", 255, 165, 0
    else:
        return "Blunder", 255, 0, 0
    
def score(e):
    if e["type"] == "mate":
            return 10000 * (-1 if e["value"] < 0 else 1)
    return e["value"]

def evaluatePosition(fen):
    board = chess.Board(fen)
    if board.is_checkmate():
        print("Checkmate! Game is over.")
        return True
    elif board.is_stalemate():
        print("Stalemate! Game is over.")
        return True
    return False

def checkValidMoveOnline(from_i, from_j, i, j):
    if not curr_board_state.arr[from_i][from_j]:
        return False
    if not checkValidPieceMove(from_i, from_j, i, j):
        print("Invalid Move. Try Again")
        return False
    return True

async def transmitLED(client):
    global ledData, LED_ROW_UUID, LED_COL_UUID, LED_R_UUID, LED_G_UUID, LED_B_UUID, DONE_UUID, doneVal

    print(ledData)
    await transmit(10, client, DONE_UUID)
    for led in ledData:
        print(f"transmitting {led.row}")
        await transmit(led.row, client, LED_ROW_UUID)
        await transmit(led.col, client, LED_COL_UUID)
        await transmit(led.r, client, LED_R_UUID)
        await transmit(led.g, client, LED_G_UUID)
        await transmit(led.b, client, LED_B_UUID)
        await transmit(1, client, DONE_UUID)

    ledData.clear()

async def transmit(data, client, UUID):
    await client.write_gatt_char(UUID, str(data).encode('utf-8'), response=True)
    time.sleep(1/1000)

async def lcdScreen(client):
    global LCD_UUID

    board = chess.Board()
    board.set_fen(curr_board_state.fen)

    turn = "White" if board.turn else "Black"
    last_move = board.peek().uci() if board.move_stack else "--"
    check = "Check!" if board.is_check() else ""

    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
        info = engine.analyse(board, chess.engine.Limit(time=0.1))
        score = info["score"].white()  # Or .black() depending on POV

        if score.is_mate():
            eval_str = f"Mate in {score.mate()}"
        else:
            eval_str = f"Eval: {score.score() / 100:.2f}"
    
    message = f"Turn: {turn}{eval_str}"
    await transmit(message, client, LCD_UUID)

asyncio.run(main())
