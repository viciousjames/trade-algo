#trial
import signal
import requests
import time
from time import sleep

#setup order parameters here
hurdle = 1
padding = 0.01
trade_quantity = 5000 #1000
order_interval = 0.2

class ApiException (Exception):
    pass


def signal_handler(signum, frame):
    global shutdown 
    signal.signal (signal.SIGINT, signal.SIG_DFL)
    shutdown = True


API_KEY = {'X-API-Key': 'NMGKWPEP'}
shutdown = False


def get_tick(session):
    resp = session.get('http://localhost:9999/v1/case')
    if resp.status_code == 401:
        raise ApiException('The API key provided in this Python code must match that in the RIT client') 
    case = resp.json()
    return case['tick']


def check_tender(session):
    resp = session.get('http://localhost:9999/v1/tenders')
    if resp.status_code == 401:
        raise ApiException('The API key provided in this Python code must match that in the RIT client')
    return resp.json()


def check_books(session, action, tender_price):
    alt_resp = session.get('http://localhost:9999/v1/securities/book?ticker=THOR_A') 
    main_resp = session.get('http://localhost:9999/v1/securities/book?ticker=THOR_M')
    if alt_resp.status_code == 401 or main_resp.status_code == 401:
        raise ApiException('The API key provided in this Python code must match that in the RIT client')
    alt_book = alt_resp.json()
    main_book = main_resp.json()
    if action == 'BUY':
        combined_volume = calc_cum_bids(alt_book['bids'], tender_price) + calc_cum_bids(main_book['bids'], tender_price)
    else:
        combined_volume = calc_cum_asks(alt_book['asks'], tender_price) + calc_cum_asks(main_book['asks'], tender_price)
    return combined_volume


def calc_cum_bids (book, tender_price):
    volume = 0
    for level in book:
        if level['price']>=tender_price+0.04:
            volume+=level['quantity']-level['quantity_filled']
    return volume

def calc_cum_asks (book, tender_price):
    volume = 0
    for level in book:
        if level['price']<=tender_price-0.04:
            volume+=level['quantity']-level['quantity_filled']
    return volume


def post_trades (session, position):
    alt_resp = session.get('http://localhost:9999/v1/securities/book?ticker=THOR_A')
    main_resp = session.get('http://localhost:9999/v1/securities/book?ticker=THOR_M')
    profit1=session.get('http://localhost:9999/v1/securities?ticker=THOR_M').json()[0]['unrealized']
    profit2=session.get('http://localhost:9999/v1/securities?ticker=THOR_A').json()[0]['unrealized']
    if alt_resp.status_code == 401 or main_resp.status_code == 401:
        raise ApiException('The API key provided in this python code must match that in the rIT client')
    alt_book = alt_resp.json()
    main_book = main_resp.json()
    if profit1>0 or profit2>0:
        if position<0:
            if alt_book['asks'][0]['price']<=main_book['asks'][0]['price']:
                lmt_trade_params = {'ticker': 'THOR_A',
                            'type': 'LIMIT',
                            'quantity': min(trade_quantity, abs(position)),
                            'price': alt_book['asks'][0]['price'],
                            'action':'BUY'}
            else:
                lmt_trade_params = {'ticker': 'THOR_M',
                            'type' : 'LIMIT',
                            'quantity': min(trade_quantity, abs(position)),
                            'price': main_book['asks'][0]['price'], 
                            'action':'BUY'}
        else:
            if alt_book['bids'][0]['price']>=main_book['bids'][0]['price']: 
                lmt_trade_params = {'ticker': 'THOR_A',
                                'type': 'LIMIT',
                                'quantity': min(trade_quantity, abs(position)),
                                'price': alt_book['bids'][0]['price'],
                                'action' : 'SELL'}
            else: 
                lmt_trade_params = {'ticker': 'THOR_M',
                                'type': 'LIMIT',
                                'quantity': min(trade_quantity, abs(position)),
                                'price': main_book['bids'][0]['price'],
                                'action':'SELL'} 
    else:
        if position<0:
            if alt_book['asks'][0]['price']<=main_book['asks'][0]['price']:
                lmt_trade_params = {'ticker': 'THOR_A',
                            'type': 'LIMIT',
                            'quantity': min(2*trade_quantity, abs(position)),
                            'price': alt_book['bids'][0]['price']+padding,
                            'action':'BUY'}
            else:
                lmt_trade_params = {'ticker': 'THOR_M',
                            'type' : 'LIMIT',
                            'quantity': min(2*trade_quantity, abs(position)),
                            'price': main_book['bids'][0]['price']+padding, 
                            'action':'BUY'}
        else:
            if alt_book['bids'][0]['price']>=main_book['bids'][0]['price']: 
                lmt_trade_params = {'ticker': 'THOR_A',
                                'type': 'LIMIT',
                                'quantity': min(2*trade_quantity, abs(position)),
                                'price': alt_book['asks'][0]['price']-padding,
                                'action' : 'SELL'}
            else: 
                lmt_trade_params = {'ticker': 'THOR_M',
                                'type': 'LIMIT',
                                'quantity': min(2*trade_quantity, abs(position)),
                                'price': main_book['asks'][0]['price']-padding,
                                'action':'SELL'}
    resp = session.post('http://Localhost:9999/v1/orders', params=lmt_trade_params)
    if resp.ok:
        lmt_order = resp. json()
        id = lmt_order['order_id']
        print('The Limit sell order was submitted and has ID', id)
        return id
    else:
        print('The order was not successfully submitted!')
        print(resp.json())
        print(lmt_trade_params)
        print(main_book['bids'][0])
        print(alt_book['bids'][0])
        raise ValueError()


def check_orders (session):
    resp=session.get('http://localhost:9999/v1/orders?status=OPEN')
    if resp.ok:
        status = resp.json()
        if len(status)>0:
            session.post('http://localhost:9999/v1/commands/cancel?all=1')
            delete = session.delete('http://localhost:9999/v1/orders/{}'.format(status[0]['order_id']))
            if delete.ok:
                print(delete.json())
    else:
        print('something wrong')

def trading_loop(session):

    position_m = session.get('http://localhost:9999/v1/securities?ticker=THOR_M').json()[0]['position']
    position_a = session.get('http://localhost:9999/v1/securities?ticker=THOR_A').json()[0]['position']

    while position_m!=0 or position_a!=0:
            post_trades (session, position_a)
            print ('working the order.. trading positions down to 0!')

           
            tender = check_tender(session)
            if len(tender)>0 and position_m<30000 and position_a>-30000:
                #if active tender presents
                print( 'Tender received, checking book...')
 
                if check_books(session, tender[0]['action'], tender[0]['price'])/tender[0]['quantity']>=hurdle:

                    resp = session.post('http://localhost:9999/v1/tenders/{}'.format (tender[0]['tender_id']))
                    if resp.ok:
                        print( 'The tender was successfully accpeted! ')
               

            sleep(order_interval)
            check_orders(session)
 
            position_m = session.get('http://localhost:9999/v1/securities?ticker=THOR_M').json()[0]['position']
            position_a = session.get ('http://Localhost:9999/v1/securities?ticker=THOR_A').json()[0]['position']

def main():

    with requests.Session() as s:

        s.headers.update(API_KEY)

        tick = get_tick(s)

        while tick < 300 and tick >0:

            
            tender = check_tender(s)
            while len(tender)>0:

                print( 'Tender received, checking book...')

                if check_books(s, tender[0]['action'], tender[0]['price'])/tender[0]['quantity']>=hurdle:

                    resp = s.post('http://localhost:9999/v1/tenders/{}'.format (tender[0]['tender_id']))
                    if resp.ok:
                        print( 'The tender was successfully accpeted!')
                else:

                    sleep(1)

                tender = check_tender(s)
                


            trading_loop(s)


            print('waiting for tender!')
            sleep(3)

            tick = get_tick(s)

        print('simulation not active')


if __name__=='__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()