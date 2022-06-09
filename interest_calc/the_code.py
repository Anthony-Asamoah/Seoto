def validation(a, b, c):
	allowed_input = [str(i) for i in range(10)] + ['.']

	for i in a:
		if i not in allowed_input:
			return False

	for j in b:
		if j not in allowed_input:
			return False

	for k in c:
		if k not in c:
			return False

	return True


class interest:
	def __init__(self, principal, rate, time):
		self.principal = float(principal)
		self.rate = float(rate)
		self.time = float(time)

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

		return f"profit = {round(profit, 2)} -> {round(percent, 2)}% | NET = {net}"

	def compound(self):
		first = (1 + (self.rate / 100)) ** (self.time - 1)
		net = self.principal * first
		profit = net - self.principal
		percent = interest.percent(profit, net)

		return f"profit = {round(profit, 2)} -> {round(percent, 2)}% | NET = {round(net, 2)}"

	def susu(self):
		net = self.principal
		profit = 0

		for iterations in range(self.time):
			profit = net * (self.rate / 100)
			net += profit + self.principal
			print(f"period {iterations + 1}: profit: {profit}, net: {net}")

		percent = interest.percent(profit, net)

		return f"profit = {round(profit, 2)} -> {round(percent, 2)}% | NET = {round(net, 2)}"

	# End of Main Methods
