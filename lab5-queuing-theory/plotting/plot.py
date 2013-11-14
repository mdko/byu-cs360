import optparse
import sys

import matplotlib
matplotlib.use('Agg')
from pylab import *

# Class that parses a file and plots several graphs
class Plotter:
	def __init__(self,file):
		""" Initialize plotter with a file name. """
		self.file = file
		self.t = []
		self.dl = []
		self.r = []

	def parse(self):
		""" Parse the data file and accumulate values for the time,
			download time, and size columns.
		"""
		first = None
		f = open(self.file)
		for line in f.readlines():
			if line.startswith("#"):
				continue
			try:
				t,download,size = line.split()
			except:
				continue
			t = float(t)
			download = float(download)
			size = int(size)
			if not first:
				first = t
			t = t - first
			self.t.append(t)
			self.dl.append(download)
			self.r.append(size*8/(download*1000000))

	def equationplot(self):
		""" Create a line graph of an equation. """
		clf()
		x = np.arange(0,9.9,0.1)
		plot(x,1/(10-x))
		xlabel('X')
		ylabel('1/(10-x)')
		savefig('equation-line.png')

	def downloadplot(self):
		""" Create a line graph of download time versus experiment time. """
		clf()
		plot(self.t,self.dl)
		xlabel('Time (seconds)')
		ylabel('Download Time (seconds)')
		savefig('download-line.png')

	def downloadboxplot(self):
		""" Create a box plot of the download time"""
		clf()
		boxplot(self.dl)
		xlabel('Attempt')
		ylabel('Download Time (seconds)')
		savefig('download-boxplot.png')

	def downloadcombined(self):
		""" Create a graph that includes a line plot of download time versus
			experiment time, plus a boxplot of the download time.
		"""
		clf()
		boxplot(self.dl,positions=[50],widths=[10])
		plot(self.t,self.dl)
		xlabel('Time (seconds)')
		ylabel('Download Time (seconds)')
		xticks(range(-5,65,5))
		savefig('download-combined.png')

	def downloadhistogram(self):
		""" Create a histogram of the download time. """
		clf()
		hist(self.dl,bins=[0.25,0.35,0.45,0.55,0.65,0.75,0.85],rwidth=0.8)
		# hist(self.dl,rwidth=0.8)
		xlabel('Download Time (seconds)')
		ylabel('Number of Downloads')
		savefig('download-histogram.png')

def parse_options():
		# parse options
		parser = optparse.OptionParser(usage = "%prog [options]",
									   version = "%prog 0.1")

		parser.add_option("-f","--file",type="string",dest="file",
						  default=None,
						  help="file")

		(options,args) = parser.parse_args()
		return (options,args)


if __name__ == '__main__':
	(options,args) = parse_options()
	if options.file == None:
		print "plot.py -f file"
		sys.exit()
	p = Plotter(options.file)
	p.parse()
	p.equationplot()
	p.downloadplot()
	p.downloadboxplot()
	p.downloadcombined()
	p.downloadhistogram()
