#input: $url, $min_int, $max_int, $strg_file_dir p.s. max_int use 0 if no ;d
import os, sys, argparse, re
import requests
import urllib.parse


temp_file="temp.ly"
pause_file="../pause.ly"
download_dir="download"
lock_suffix=".lock.ly"

class Temp_data:
	def __init__(self, f_temp_arr):
		for i in range(1, 6):
			f_temp_arr[i] = int(f_temp_arr[i])
		self.url_template, \
		self.min_int, \
		self.max_int, \
		self.is_numbering, \
		self.current_strg_counter, \
		self.current_counter \
		 = f_temp_arr

	def __str__(self):
		return str(self.__dict__)

	def update_temp(self, f_temp):
		f_temp.seek(0)
		#f_temp.write('\n'.join(map(str, list(temp_data.values()))))
		f_temp.write('\n'.join(map(str, self.__dict__.values())))
		f_temp.write('\n')
		f_temp.truncate()
		#force flushing
		f_temp.flush()
		os.fsync(f_temp.fileno())

#def convert_int(arr, start, end):
#	return_arr = arr
#	for i in range(start, end+1):
#		arr[i] = int(arr[i])
#	return return_arr

#def extract_cookie(cookie_file):
#	if cookie_file is not None:
#		cookies = {}
#		with open(cookie_file) as f_cookie:
#			#cookies = f_cookie.read().splitlines()
#			for cookies_lines in f_cookie:
#				cookies_split = cookies_lines.split(':', 1)
#				if cookies_split[0].lower().strip() == 'cookie':
#					for cookie in cookies_split[1].split(';'):
#						name, value = [i.strip() for i in cookie.split('=', 1)]
#						cookies.update({name: value})
#					return cookies
#	return None

def extract_headers(header_file):
	if header_file is not None:
		headers = {}
		with open(header_file) as f_header:
			for headers_lines in f_header:
				headers_split = headers_lines.split(':', 1)
				headers_split = [i.strip() for i in headers_split]
				headers.update({headers_split[0]: headers_split[1]})
		return headers
	return None

def grep_content_disposition(dispos_strg):
	try:
		name = re.search("filename[^=]*\*[^=]*=[^;]*", dispos_strg, re.IGNORECASE)
		if name is not None:
			name = name.group()
			name = name[name.rindex("'")+1:]
		else:
			name = re.search('filename[^=*]*=[^;]*', dispos_strg, re.IGNORECASE)
			print(name)
			if name is not None:
				name = name.group()
				name = name.split('"')
				#name = name[1:len(name)-2]
		return urllib.parse.unquote(name)
	except:
		print('grep_content_disposition exception, response headers')
		return None

def dl_resource(f_temp, temp_data, line, headers):
	for temp_data.current_counter in range(temp_data.current_counter, temp_data.max_int+1):
		temp_data.update_temp(f_temp)
		try:
			os.remove(filename)
		except OSError:
			pass

		url = temp_data.url_template.replace(';s', line).replace(';d', str(temp_data.current_counter))

		r = requests.get(url, allow_redirects=True, headers=headers)
		if 'content-disposition' in r.headers:		#r.headers is caseinsensitive-type dict
			fname = grep_content_disposition(r.headers['content-disposition'])
			print(str(fname))
		else:
			fname = urllib.parse.unquote(r.url[r.url.rindex('/')+1:])

		print(fname, end='')
		try:
			byte = open(fname, 'wb').write(r.content)
			if not byte > 0:
				print('[E]')
			else:
				print('[S]')
		except:
			print('[E] wf')		#write file err


#		remotefile = urlopen(url, cookies=cookies)
#		blah = remotefile.info()['Content-Disposition']
#		value, params = cgi.parse_header(blah)
#		filename = params["filename"]
#		urlretrieve(url, filename)


parser = argparse.ArgumentParser(description='Optional app description')
parser.add_argument('-url', '--url_template',
                    help='url template: [;d]:num_replace [;s]:strg_replace',
                    required=True)
parser.add_argument('-min', '--min_int',
                    help='counter start int')
parser.add_argument('-max', '--max_int',
                    help='counter end int')
parser.add_argument('-num', '--is_numbering',
                    help='use name from counter / strg file')
parser.add_argument('-strg', '--strg_file',
                    help='string file')
parser.add_argument('-cookie', '--cookie_file',
                    help='cookie file')
args = parser.parse_args()
if args.strg_file is not None:
	args.strg_file = os.path.realpath(args.strg_file)
if args.cookie_file is not None:
	args.cookie_file = os.path.realpath(args.cookie_file)

if ";d" in args.url_template:
	args.max_int = '0' if args.max_int is None else args.max_int
	args.min_int = '0' if args.min_int is None else args.min_int
else:
	args.max_int = '0'
	args.min_int = '0'
args.is_numbering = args.is_numbering or '1'

if not os.path.exists(temp_file):
	with open(temp_file, "w") as f_temp:
		f_temp.write('\n'.join([args.url_template,
								args.min_int,
								args.max_int,
								args.is_numbering,
								'1',
								args.min_int,
								'']))

with open(temp_file, "r+") as f_temp:
	temp_data = Temp_data(f_temp.read().splitlines())

	if not os.path.exists(download_dir):
	   os.makedirs(download_dir)
	os.chdir(download_dir)
	temp_file = "../"+temp_file

	#cookie
	#cookies = extract_cookie(args.cookie_file)
	headers = extract_headers(args.cookie_file)
	#end of cookie
			
	if args.strg_file is None:
		dl_resource(f_temp, temp_data, "", cookies)
	else:
		with open(args.strg_file, "r") as f_strg:

			for j, line in enumerate(f_strg):
				if j+1 >= temp_data.current_strg_counter:
					#print(j, line, end='')
					line = line.rstrip('\r\n')
					temp_data.current_strg_counter = j+1
					dl_resource(f_temp, temp_data, line, headers)
					temp_data.current_counter = temp_data.min_int
