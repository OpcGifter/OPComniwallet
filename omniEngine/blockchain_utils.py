import simplejson
import requests
import decimal
import json
from config import BTAPIKEY
from rpcclient import gettxout
from cacher import *
import config

if config.TESTNET:
  # neither blockchain.info nor blockonomics support testnet
  BLOCKCHAININFO_API_URL = "https://blockchain.info"
  BLOCKONOMICS_API_URL = "https://www.blockonomics.co/api"
  
  BLOCKTRAIL_API_URL = "https://api.blocktrail.com/v1/tbtc"
  BLOCKCYPHER_API_URL = "https://api.blockcypher.com/v1/btc/test3"
  BITGO_API_URL = "https://test.bitgo.com/api/v1"
else:
  BLOCKCHAININFO_API_URL = "https://blockchain.info"
  BLOCKTRAIL_API_URL = "https://api.blocktrail.com/v1/btc"
  BLOCKCYPHER_API_URL = "https://api.blockcypher.com/v1/btc/main"
  BITGO_API_URL = "https://www.bitgo.com/api/v1"
  BLOCKONOMICS_API_URL = "https://www.blockonomics.co/api"

try:
  expTime=config.BTCBAL_CACHE
except:
  expTime=600

def bc_getutxo(address, ramount, page=1, retval=None, avail=0):
  if retval==None:
    retval=[]
  try:
    r = requests.get(BLOCKTRAIL_API_URL + '/address/'+address+'/unspent-outputs?api_key='+str(BTAPIKEY)+'&limit=200&page='+str(page))
    if r.status_code == 200:
      response = r.json()
      unspents = response['data']
      print "got unspent list (btrail)", response
      for tx in unspents:
        txUsed=gettxout(tx['hash'],tx['index'])
        isUsed = ('result' in txUsed and txUsed['result']==None)
        if not isUsed and txUsed['result']['confirmations'] > 0 and tx['multisig']==None:
          avail += tx['value']
          retval.append([ tx['hash'], tx['index'], tx['value'] ])
          if avail >= ramount:
            return {"avail": avail, "utxos": retval, "error": "none"}
      if int(response['total'])-(int(response['per_page'])*page ) > 0:
        return bc_getutxo(address, ramount, page+1, retval, avail)
      return {"avail": avail, "error": "Low balance error"}
    else:
      #return {"error": "Connection error", "code": r.status_code}
      return bc_getutxo_blockcypher(address, ramount)
  except:
    return bc_getutxo_blockcypher(address, ramount)


def bc_getutxo_blockcypher(address, ramount):
  try:
    r = requests.get(BLOCKCYPHER_API_URL + '/addrs/'+address+'?unspentOnly=true')

    if r.status_code == 200:
      unspents = r.json()['txrefs']
      print "got unspent list (bcypher)", unspents

      retval = []
      avail = 0
      for tx in unspents:
        txUsed=gettxout(tx['tx_hash'],tx['tx_output_n'])
        isUsed = ('result' in txUsed and txUsed['result']==None)
        if tx['confirmations'] > 0 and not isUsed:
          avail += tx['value']
          retval.append([ tx['tx_hash'], tx['tx_output_n'], tx['value'] ])
          if avail >= ramount:
            return {"avail": avail, "utxos": retval, "error": "none"}
      return {"avail": avail, "error": "Low balance error"}
    else:
      return {"error": "Connection error", "code": r.status_code}
  except:
    return {"error": "Connection error", "code": r.status_code}


def bc_getpubkey(address):
  # note: only supports mainnet
  try:
    if config.TESTNET:
      return "error: tried using blockchain.info api with testnet enabled"
    
    r = requests.get(BLOCKCHAININFO_API_URL + '/q/pubkeyaddr/'+address)

    if r.status_code == 200:
      return str(r.text)
    else:
      return "error"
  except:
    return "error"

def bc_getbalance(address):
  try:
    balance=rGet("omniwallet:balances:address:"+str(address))
    balance=json.loads(balance)
    if balance['error']:
      raise LookupError("Not cached")
  except Exception as e:
    balance = bc_getbalance_bitgo(address)
    #cache btc balance for 2.5 minutes
    rSet("omniwallet:balances:address:"+str(address),json.dumps(balance))
    rExpire("omniwallet:balances:address:"+str(address),expTime)
  return balance

def bc_getbalance_bitgo(address):
  try:
    r= requests.get(BITGO_API_URL + '/address/'+address)
    if r.status_code == 200:
      #balance = int(r.json()['confirmedBalance'])
      balance = int(r.json()['balance'])
      return {"bal":balance , "error": None}
    else:
      return bc_getbalance_blockcypher(address)
  except:
    return bc_getbalance_blockcypher(address)

def bc_getbalance_blockcypher(address):
  try:
    r= requests.get(BLOCKCYPHER_API_URL + '/addrs/'+address+'/balance')
    if r.status_code == 200:
      balance = int(r.json()['balance'])
      return {"bal":balance , "error": None}
    else:
      return {"bal": 0 , "error": "Couldn't get balance"}
  except:
    return {"bal": 0 , "error": "Couldn't get balance"}

def bc_getbulkbalance(addresses):
  split=[]
  recurse=[]
  counter=0
  retval={}
  cbdata={}
  for a in addresses:
    try:
      cb=rGet("omniwallet:balances:address:"+str(a))
      cb=json.loads(cb)
      if cb['error']:
        raise LookupError("Not cached")
      else:
        cbdata[a]=cb['bal']
    except Exception as e:
      if counter < 20:
        split.append(a)
      else:
        recurse.append(a)
      counter+=1

  if len(split)==0:
    if len(cbdata) > 0:
      retval={'bal':cbdata, 'fresh':None}
    else:
      retval={'bal':{}, 'fresh':None}
  else:
    try:
      data=bc_getbulkbalance_blockonomics(split)
      if data['error']:
        raise Exception("issue getting blockonomics baldata",data)
      else:
        retval={'bal':dict(data['bal'],**cbdata), 'fresh':split}
    except Exception as e:
      print e
      try:
        data=bc_getbulkbalance_blockchain(split)
        if data['error']:
          raise Exception("issue getting blockchain baldata",data)
        else:
          retval={'bal':dict(data['bal'],**cbdata), 'fresh':split}
      except Exception as e:
        print e
        if len(cbdata) > 0:
          retval={'bal':cbdata, 'fresh':None}
        else:
          retval={'bal':{}, 'fresh':None}


  rSetNotUpdateBTC(retval)
  if len(recurse)>0:
    rdata=bc_getbulkbalance(recurse)
  else:
    rdata={}
  return dict(retval['bal'],**rdata)

      
def bc_getbulkbalance_blockonomics(addresses):
  formatted=""
  for address in addresses:
    if formatted=="":
      formatted=address
    else:
      formatted=formatted+" "+address

  try:
    if config.TESTNET:
      return "error: tried using blockonomics api with testnet enabled"
    
    r = requests.post(BLOCKONOMICS_API_URL + '/balance',json.dumps({"addr":formatted}))
    if r.status_code == 200:
      balances = r.json()['response']
      retval = {}
      for entry in balances:
        retval[entry['addr']] = int(entry['confirmed'])+int(entry['unconfirmed'])
      return {"bal": retval, "error": None}
    else:
      return {"bal": None , "error": True}
  except:
    return {"bal": None , "error": True}

def bc_getbulkbalance_blockchain(addresses):
  formatted=""
  for address in addresses:
    if formatted=="":
      formatted=address
    else:
      formatted=formatted+"|"+address
  try:
    if config.TESTNET:
      return "error: tried using blockchain.info api with testnet enabled"
    
    r= requests.get(BLOCKCHAININFO_API_URL + '/balance?active='+formatted)
    if r.status_code == 200:
      balances = r.json()
      retval = {}
      for entry in balances:
        retval[entry] = int(balances[entry]['final_balance'])
      return {"bal": retval, "error": None}
    else:
      return {"bal": None , "error": True}
  except:
    return {"bal": None , "error": True}
