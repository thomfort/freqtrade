import enum
import logging
from typing import List

from bittrex.bittrex import Bittrex
from poloniex import Poloniex
from wrapt import synchronized

logger = logging.getLogger(__name__)

_exchange_api = None


class Exchange(enum.Enum):
    POLONIEX = 0
    BITTREX = 1


class ApiWrapper(object):
    """
    Wrapper for exchanges.
    Currently implemented:
        * Bittrex
        * Poloniex (partly)
    """
    def __init__(self, config: dict):
        """
        Initializes the ApiWrapper with the given config,
        it does basic validation whether the specified
        exchange and pairs are valid.
        :param config: dict
        """
        self.dry_run = config['dry_run']
        if self.dry_run:
            logger.info('Instance is running with dry_run enabled')

        use_poloniex = config.get('poloniex', {}).get('enabled', False)
        use_bittrex = config.get('bittrex', {}).get('enabled', False)

        if use_poloniex:
            self.exchange = Exchange.POLONIEX
            self.api = Poloniex(key=config['poloniex']['key'], secret=config['poloniex']['secret'])
        elif use_bittrex:
            self.exchange = Exchange.BITTREX
            self.api = Bittrex(api_key=config['bittrex']['key'], api_secret=config['bittrex']['secret'])
        else:
            self.api = None
            raise RuntimeError('No exchange specified. Aborting!')

        # Check if all pairs are available
        markets = self.get_markets()
        for pair in config[self.exchange.name.lower()]['pair_whitelist']:
            if pair not in markets:
                raise RuntimeError('Pair {} is not available at Poloniex'.format(pair))

    def buy(self, pair: str, rate: float, amount: float) -> str:
        """
        Places a limit buy order.
        :param pair: Pair as str, format: BTC_ETH
        :param rate: Rate limit for order
        :param amount: The amount to purchase
        :return: order_id of the placed buy order
        """
        if self.dry_run:
            pass
        elif self.exchange == Exchange.POLONIEX:
            self.api.buy(pair, rate, amount)
            # TODO: return order id
        elif self.exchange == Exchange.BITTREX:
            data = self.api.buy_limit(pair.replace('_', '-'), amount, rate)
            if not data['success']:
                raise RuntimeError('BITTREX: {}'.format(data['message']))
            return data['result']['uuid']

    def sell(self, pair: str, rate: float, amount: float) -> str:
        """
        Places a limit sell order.
        :param pair: Pair as str, format: BTC_ETH
        :param rate: Rate limit for order
        :param amount: The amount to sell
        :return: None
        """
        if self.dry_run:
            pass
        elif self.exchange == Exchange.POLONIEX:
            self.api.sell(pair, rate, amount)
            # TODO: return order id
        elif self.exchange == Exchange.BITTREX:
            data = self.api.sell_limit(pair.replace('_', '-'), amount, rate)
            if not data['success']:
                raise RuntimeError('BITTREX: {}'.format(data['message']))
            return data['result']['uuid']

    def get_balance(self, currency: str) -> float:
        """
        Get account balance.
        :param currency: currency as str, format: BTC
        :return: float
        """
        if self.dry_run:
            return 999.9
        elif self.exchange == Exchange.POLONIEX:
            data = self.api.returnBalances()
            return float(data[currency])
        elif self.exchange == Exchange.BITTREX:
            data = self.api.get_balance(currency)
            if not data['success']:
                raise RuntimeError('BITTREX: {}'.format(data['message']))
            return float(data['result']['Balance'] or 0.0)

    def get_ticker(self, pair: str) -> dict:
        """
        Get Ticker for given pair.
        :param pair: Pair as str, format: BTC_ETC
        :return: dict
        """
        if self.exchange == Exchange.POLONIEX:
            data = self.api.returnTicker()
            return {
                'bid': float(data[pair]['highestBid']),
                'ask': float(data[pair]['lowestAsk']),
                'last': float(data[pair]['last'])
            }
        elif self.exchange == Exchange.BITTREX:
            data = self.api.get_ticker(pair.replace('_', '-'))
            if not data['success']:
                raise RuntimeError('BITTREX: {}'.format(data['message']))
            return {
                'bid': float(data['result']['Bid']),
                'ask': float(data['result']['Ask']),
                'last': float(data['result']['Last']),
            }

    def cancel_order(self, order_id: str) -> None:
        """
        Cancel order for given order_id
        :param order_id: id as str
        :return: None
        """
        if self.dry_run:
            pass
        elif self.exchange == Exchange.POLONIEX:
            raise NotImplemented('Not implemented')
        elif self.exchange == Exchange.BITTREX:
            data = self.api.cancel(order_id)
            if not data['success']:
                raise RuntimeError('BITTREX: {}'.format(data['message']))

    def get_open_orders(self, pair: str) -> List[dict]:
        """
        Get all open orders for given pair.
        :param pair: Pair as str, format: BTC_ETC
        :return: list of dicts
        """
        if self.dry_run:
            return []
        elif self.exchange == Exchange.POLONIEX:
            raise NotImplemented('Not implemented')
        elif self.exchange == Exchange.BITTREX:
            data = self.api.get_open_orders(pair.replace('_', '-'))
            if not data['success']:
                raise RuntimeError('BITTREX: {}'.format(data['message']))
            return [{
                'id': entry['OrderUuid'],
                'type': entry['OrderType'],
                'opened': entry['Opened'],
                'rate': entry['PricePerUnit'],
                'amount': entry['Quantity'],
                'remaining': entry['QuantityRemaining'],
            } for entry in data['result']]

    def get_pair_detail_url(self, pair: str) -> str:
        """
        Returns the market detail url for the given pair
        :param pair: pair as str, format: BTC_ANT
        :return: url as str
        """
        if self.exchange == Exchange.POLONIEX:
            raise NotImplemented('Not implemented')
        elif self.exchange == Exchange.BITTREX:
            return 'https://bittrex.com/Market/Index?MarketName={}'.format(pair.replace('_', '-'))

    def get_markets(self) -> List[str]:
        """
        Returns all available markets
        :return: list of all available pairs
        """
        if self.exchange == Exchange.POLONIEX:
            # TODO: implement
            raise NotImplemented('Not implemented')
        elif self.exchange == Exchange. BITTREX:
            data = self.api.get_markets()
            if not data['success']:
                raise RuntimeError('BITTREX: {}'.format(data['message']))
            return [m['MarketName'].replace('-', '_') for m in data['result']]


@synchronized
def get_exchange_api(conf: dict) -> ApiWrapper:
    """
    Returns the current exchange api or instantiates a new one
    :return: exchange.ApiWrapper
    """
    global _exchange_api
    if not _exchange_api:
        _exchange_api = ApiWrapper(conf)
    return _exchange_api
