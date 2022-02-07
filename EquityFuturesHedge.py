import csv
import Balanz_REST_r as balanz
#import xlwings as xw
import time
import datetime as dt
import signal
import sys

#Cantidad de indices Spot
cantidadIndices = 55

loggedOut = False
merval = {}
mervalS = {}
no_merv = []

def on_marketdata(tipo, data):
    if(tipo == 1):
        #aca va el codigo de manejo de market data
        return(data["ticker"],data["plazo"],data["mo"],data["cc"],data["pc"],data["pv"],data["cv"],data["u"],data["ant"],data["v"])
    if(tipo == 2):
        #aca va el manejo de indice merval si es necesario.
        print("Indice Merval", data)
        
def signal_handler(signal, frame):
    print("You pressed Ctrl+C!")
    balanz.logout()
    sys.exit(0)

def ejecutarOrden(ticker, size, precioC):
    idOrderC = balanz.operarBYMA(1351, 1, ticker, 2, size, precioC, 1)
    return(int(idOrderC))

with open('RFX20.csv', 'r') as csvfile:
    cMerval = csv.reader(csvfile, delimiter = ',')
    for row in cMerval:
        merval[row[0]] = int(round(cantidadIndices * float(row[1]),0))

with open('RFX20 - Referencia.csv', 'r') as csvfile:
    rMerval = csv.reader(csvfile, delimiter = ',')
    for row in rMerval:
        aux = {}
        CI = {}
        DosCuatro = {}
        CuatroOcho = {}
        CI['bidSize'] = row[1]
        CI['bid'] = row[2]
        CI['last'] = row[3]
        CI['ask'] = row[4]
        CI['askSize'] = row[5]
        DosCuatro['bidSize'] = row[6]
        DosCuatro['bid'] = row[7]
        DosCuatro['last'] = row[8]
        DosCuatro['ask'] = row[9]
        DosCuatro['askSize'] = row[10]
        CuatroOcho['bidSize'] = row[11]
        CuatroOcho['bid'] = row[12]
        CuatroOcho['last'] = row[13]
        CuatroOcho['ask'] = row[14]
        CuatroOcho['askSize'] = row[15]
        aux['CI'] = CI
        aux['24hs'] = DosCuatro
        aux['48hs'] = CuatroOcho
        mervalS[row[0]] = aux

#inicializo la API de Balanz. (URL, usuario, password, codigo4D, callbackMarketData)

#Datos para produccion
balanz.init("https://users.balanz.com/asesores", "accountname", "username", "pass", on_marketdata)

#Datos para desarrollo
#balanz.init("http://desa-01:8085", "accountname2", "username2", "pass", on_marketdata)
while sum(merval.values())>0:
    try:
        #print('paso 1')
        mervalData = balanz.GetMarketData(on_marketdata)
        #print('paso 2')
        compraMerval= open('compraRFX20.csv','a')
        #print('paso 3')
        for acc in mervalData:
            try:
                #print(contador)
                mervalS[acc[0]][acc[1]]['bidSize'] = int(acc[3])
                mervalS[acc[0]][acc[1]]['bid'] = float(acc[4])
                mervalS[acc[0]][acc[1]]['last'] = float(acc[7])
                mervalS[acc[0]][acc[1]]['ask'] = float(acc[5])
                mervalS[acc[0]][acc[1]]['askSize'] = int(acc[6])
            except:
                no_merv.append(acc[0])
                #print(str(acc)+' No pertenece al merval')
        for acc in merval:
            if merval[acc]>0:
                size = min(mervalS[acc]['48hs']['askSize'], merval[acc])
                orderId = ejecutarOrden(acc, size ,mervalS[acc]['48hs']['ask'])
                if orderId >0:
                    compraMerval.write(acc + ';' + str(mervalS[acc]['48hs']['ask']) + ';' + str(size) + ';' + str(orderId) +'\n')
                    merval[acc] = merval[acc] - size
                    if merval[acc] <0 :
                        print('Error, se operaron acciones por demas en ' + acc + '. Hay '+ merval[acc])
                compraMerval.close()
                time.sleep(2)
                break
    except:
        print('Ha ocurrido un error, continuamos operando')




if loggedOut != True:
    balanz.logout()
    signal.signal(signal.SIGINT, signal_handler)
