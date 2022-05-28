class interest:
	def __init__(self, principal, rate, time):
		self.principal = int(principal)
		self.rate = int(rate)
		self.time = int(time)

	def __str__(self):
		return "cumulative interest calculator"

	# Utility Methods
	def percent(profit, net):
		percent = ((profit / net) * 100)
		return percent

	# End Of Utilities

	# Main Methods

	def simple(self):
		profit = (self.principal * self.time) * (self.rate / 100)
		net = profit + self.principal
		percent = interest.percent(profit, net)

		return f"profit = {round(profit, 2)} and NET = {net}\nprofit gained = {round(percent, 2)}%"

	def compound(self):
		first = (1 + (self.rate / 100)) ** (self.time - 1)
		net = self.principal * first
		profit = net - self.principal
		percent = interest.percent(profit, net)

		return f"profit = {round(profit, 2)} and NET = {round(net, 2)}\n profit gained = {round(percent, 2)}%"

	def susu(self):
		net = self.principal
		profit = 0

		for iterations in range(self.time):
			profit = net * (self.rate / 100)
			net += profit + self.principal
			print(f"period {iterations + 1}: profit: {profit}, net: {net}")

		percent = interest.percent(profit, net)

		return f"profit = {round(profit, 2)} and NET = {round(net, 2)}.\n profit gained was {round(percent, 2)}%"

	# End of Main Methods
