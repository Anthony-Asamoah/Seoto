import logging
import string


class Calculator:
    def __init__(self, principal, rate, time, kind):
        self.is_valid(principal, rate, time, kind)
        self.kind = kind
        self.principal = float(principal)
        self.rate = float(rate)
        self.time = int(time)

    def __str__(self):
        return f"Calculate Calculator on {self.principal} @ {self.rate} by {self.time} times"

    def get_result(self):
        function_map = {
            '1': self.simple,
            '2': self.compound,
            '3': self.susu
        }
        return function_map.get(self.kind)()

    def get_chart_data(self):
        chart_map = {
            '1': self._chart_simple,
            '2': self._chart_compound,
            '3': self._chart_susu
        }
        return chart_map.get(self.kind)()

    def _chart_simple(self):
        data = []
        for period in range(1, self.time + 1):
            profit = self.principal * period * (self.rate / 100)
            data.append({'period': period, 'principal': round(self.principal, 2), 'profit': round(profit, 2)})
        return data

    def _chart_compound(self):
        data = []
        for period in range(1, self.time + 1):
            net = self.principal * (1 + self.rate / 100) ** period
            profit = net - self.principal
            data.append({'period': period, 'principal': round(self.principal, 2), 'profit': round(profit, 2)})
        return data

    def _chart_susu(self):
        data = []
        principal_sum = 0
        net = 0
        profit = 0
        for period in range(1, self.time + 1):
            principal_sum += self.principal
            net += self.principal
            profit += (net * (self.rate / 100))
            net += profit
            cumulative_profit = net - principal_sum
            data.append({'period': period, 'principal': round(principal_sum, 2), 'profit': round(cumulative_profit, 2)})
        return data

    def simple(self):
        profit = (self.principal * self.time) * (self.rate / 100)
        net = profit + self.principal
        percent = self.percent(profit, self.principal)
        return [
            f"{round(profit, 2)} Profit",
            f"{round(percent, 2)}% Return",
            f"NET amount = {net}"
        ]

    def compound(self):
        first = (1 + (self.rate / 100)) ** ((self.time + 1) - 1)
        net = self.principal * first
        profit = net - self.principal
        percent = self.percent(profit, self.principal)
        return [
            f"{round(profit, 2)} Profit",
            f"{round(percent, 2)}% Return",
            f"NET amount = {round(net, 2)}"
        ]

    def susu(self):
        principal_sum = 0
        net = 0
        profit = 0

        for i in range(self.time):
            principal_sum += self.principal
            net += self.principal
            profit += (net * (self.rate / 100))
            net += profit

        net_profit = net - principal_sum
        percent = self.percent(net_profit, principal_sum)
        return [
            f"{round(net_profit, 2)} Profit",
            f"{round(percent, 2)}% Return",
            f"NET Principal = {round(principal_sum, 2)}",
            f"NET Amount = {round(net, 2)}"
        ]

    @staticmethod
    def percent(profit, principal):
        percent = ((profit / principal) * 100)
        return percent

    allowed_input = string.digits
    allowed_input += '.'
    allowed_kind_input = ['1', '2', '3']

    @classmethod
    def is_valid(cls, principal: str, rate: str, time: str, kind: str) -> None:
        if kind not in cls.allowed_kind_input:
            logging.critical(f"Invalid input for 'Kind'. expected one of: {cls.allowed_kind_input} but got {kind}")
            raise ValueError(f"An error occurred.")
        if not principal or principal == '0': raise ValueError("Principal must be a value greater than 0")
        if not rate or rate == '0': raise ValueError("Rate must be a value greater than 0")
        if not time or time == '0': raise ValueError("Time must be a value greater than 0")
        if '.' in time: raise ValueError("Time must be an integer (whole number, not a fraction/decimal)")
        cls._is_valid_str(principal, 'principal')
        cls._is_valid_str(rate, 'rate')
        cls._is_valid_str(time, 'time')

    @classmethod
    def _is_valid_str(cls, value: str, label: str) -> None:
        for i in value:
            if i not in cls.allowed_input:
                raise ValueError(f'Character not allowed in {label}: {i}')
