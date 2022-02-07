import csv
import Balanz_REST_r as balanz
import time
import datetime as dt
import signal
import sys

##Variables a controlar / cambiar
#Comision
comision = 0.00001
#Monto a invertir
inversion = 500000
#Minima ganancia por la cual arbitrar
minGan = 30
#El costo del dinero
costoOp = 0.47
#Dias entre plazos
diasCI24 = 1
diasCI48 = 2
dias2448 = 1

print('Recordar cambiar dias, actualmente estan en: ' + str(diasCI24) + ', ' + str(diasCI48) + ', ' + str(dias2448))

#Variables internas
parar = False
contador = 0
loggedOut = False

#Creando el diccionario de acciones y plazos
bonos ={}
no_bonos = []
with open('Bonos - Referencia JMR.csv', 'r') as csvfile:
    rBonos = csv.reader(csvfile, delimiter = ',')
    for row in rBonos:
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
        bonos[row[0]] = aux


def calculoArbitraje(val1, size1, val2, size2, plazo):
    global comision, inversion
    if (size1>0 and size2>0):
        tasa = ((val1*(1-comision))/(val2*(1+comision))-1)/plazo*365
        #print(tasa)
        resultado = min(size1,size2)*((val1*(1-comision))-(val2*(1+comision)))
        #print(resultado)
        return([resultado, tasa, min(size1,size2, int(inversion/val2))])
    else:
        return([0, 0, 0])

def ejecutarOrden(ticker, size, compra, plazoCompra, venta, plazoVenta):
    idOrderC = balanz.operarBYMA(1351, 1, ticker, plazoCompra, size, compra, 1)
    if (idOrderC != -1):
        idOrderV = balanz.operarBYMA(1351, 2, ticker, plazoVenta, size, venta, 1)
        return([int(idOrderC), int(idOrderV)])
    else:
        return([-1,-1])

def on_marketdata(tipo, data):
    if(tipo == 1):
        #aca va el codigo de manejo de market data
        return(data["ticker"],data["plazo"],data["mo"],data["cc"],data["pc"],data["pv"],data["cv"],data["u"],data["ant"],data["v"])
    if(tipo == 2):
        #aca va el manejo de indice bonos si es necesario.
        #print("Bonos", data)
        return(data["ticker"],data["plazo"],data["mo"],data["cc"],data["pc"],data["pv"],data["cv"],data["u"],data["ant"],data["v"])
    if(tipo == 3):
        #aca va el manejo de indice bonos si es necesario.
        #print("Watch", data)
        return(data["ticker"],data["plazo"],"",data["cc"],data["pc"],data["pv"],data["cv"],data["u"],data["ant"],data["v"])
        
def signal_handler(signal, frame):
    print("You pressed Ctrl+C!")
    balanz.logout()
    sys.exit(0)
        
##Comentar y descomentar para conectar con desarrollo o produccion.
#inicializo la API de Balanz. (URL, usuario, password, codigo4D, callbackMarketData)

#Datos para produccion
balanz.init("http://desa-01:8085", "accountname", "username", "pass", on_marketdata)
#Datos para desarrollo
#balanz.init("http://desa-01:8085", "accountname2", "username2", "pass", on_marketdata)

##Descomentar el while (y comentar el for) para que corra sin parar, sino 360 iteraciones son 30mins aprox
#while True==True:
for i in range(0,360):
    try:
        if parar==True:
            break
        #bonos = blank
        bonosData = balanz.GetMarketDataWatch(on_marketdata)
        #print(bonosData)
        arbitrajes = open('ArbitrajesBonos.csv','a')
        for acc in bonosData:
            try:
                #print(contador)
                bonos[acc[0]][acc[1]]['bidSize'] = int(acc[3])
                bonos[acc[0]][acc[1]]['bid'] = float(acc[4])
                bonos[acc[0]][acc[1]]['last'] = float(acc[7])
                bonos[acc[0]][acc[1]]['ask'] = float(acc[5])
                bonos[acc[0]][acc[1]]['askSize'] = int(acc[6])
            except:
                no_bonos.append(acc[0])
                #print(str(acc)+' No pertenece al bonos')
        #print(blank)
        for acc in bonos:
            aCI48 = calculoArbitraje(bonos[acc]['48hs']['bid'],bonos[acc]['48hs']['bidSize'],bonos[acc]['CI']['ask'], bonos[acc]['CI']['askSize'], diasCI48)
            #print(aCI48)
            if (aCI48[0]>minGan and aCI48[1]>costoOp):
                arbitrajeCI48 = ejecutarOrden(acc, aCI48[2],bonos[acc]['CI']['ask'],0,bonos[acc]['48hs']['bid'],2)
                if (arbitrajeCI48[0] > 0 and arbitrajeCI48[1] > 0):
                    arbitrajes.write(str(dt.datetime.now())+";"+acc+";"+'CI'+";"+str(aCI48[2])+";"+str(bonos[acc]['CI']['ask'])+";"+str(bonos[acc]['48hs']['bid'])+";"+str(aCI48[2])+";"+'48hs'+'\n')
                    continue
                else:
                    print('Error operando '+ acc +' en CI contra 48hs')
                    parar = True
                    break

            a2448 = calculoArbitraje(bonos[acc]['48hs']['bid'],bonos[acc]['48hs']['bidSize'],bonos[acc]['24hs']['ask'], bonos[acc]['24hs']['askSize'], dias2448)
            #print(a2448)
            if (a2448[0]>minGan and a2448[1]>costoOp):
                arbitraje2448 = ejecutarOrden(acc, a2448[2],bonos[acc]['24hs']['ask'],1,bonos[acc]['48hs']['bid'],2)
                if (arbitraje2448[0] > 0 and arbitraje2448[1] > 0):
                    arbitrajes.write(str(dt.datetime.now())+";"+acc+";"+'24hs'+";"+str(a2448[2])+";"+str(bonos[acc]['24hs']['ask'])+";"+str(bonos[acc]['48hs']['bid'])+";"+str(a2448[2])+";"+'48hs'+'\n')
                    continue
                else:
                    print('Error operando '+ acc +' en 24hs contra 48hs')
                    parar = True
                    break

            aCI24 = calculoArbitraje(bonos[acc]['24hs']['bid'],bonos[acc]['24hs']['bidSize'],bonos[acc]['CI']['ask'], bonos[acc]['CI']['askSize'], diasCI24)
            #print(aCI24)
            if (aCI24[0]>minGan and aCI24[1]>costoOp):
                arbitrajeCI24 = ejecutarOrden(acc,aCI24[2],bonos[acc]['CI']['ask'],0,bonos[acc]['24hs']['bid'],1)
                if (arbitrajeCI24[0] > 0 and arbitrajeCI24[1] > 0):
                    arbitrajes.write(str(dt.datetime.now())+";"+acc+";"+'CI'+";"+str(aCI24[2])+";"+str(bonos[acc]['CI']['ask'])+";"+str(bonos[acc]['24hs']['bid'])+";"+str(aCI24[2])+";"+'24hs'+'\n')
                    continue
                else:
                    print('Error operando '+ acc +' en CI contra 24hs')
                    parar = True
                    break
        time.sleep(5)
        print(aCI48)
        print(aCI24)
        print(a2448)
    except KeyboardInterrupt:
        arbitrajes.close()
        balanz.logout()
        loggedOut = True
        break
        signal.signal(signal.SIGINT, signal_handler)
    
            

        #arbitrajes.write(accion+";"+plazoCompra+";"+size+";"+compra+";"+venta+";"+size+";"+plazoVenta+'\n')
    arbitrajes.close()

if loggedOut != True:
    balanz.logout()
    signal.signal(signal.SIGINT, signal_handler)
