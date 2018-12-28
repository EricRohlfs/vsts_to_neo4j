"""
Helps build out information to make general VSTS HTTP requests
"""
import time
import base64
import json
import urllib.request
import os
import configparser

class VstsInfo(object):
    """
    Started out as a class to help build vsts requests, now actually makes them
    and saves results to file before passing off for processing.
    """

    def __init__(self, personal_access_token, project_name, data_folder='../DevMrgDataCache'):
        # todo: remove personal access token from the __init__ signature
        self.config = configparser.ConfigParser()
        self.config.read_file(open('default.cfg'))

        #todo: get these items out of this class,
        #      let each module build their own url with help from this class.
        self.project_name = project_name
        self._load_from_source = False

    @property
    def crawl_throttle(self):
        return float(self.config['DEFAULT']['crawl_throttle'])

    @property
    def project_whitelist(self):
        """
        List the projects you wish to crawl
        """
        return self.config['DEFAULT']['project_whitelist'].split(",")

    @property
    def personal_access_token(self):
        """
        Access token supplied by VSTS to give permission to read the data.
        """
        pat = self.config['DEFAULT']['personal_access_token']
        if not pat.startswith(":"):
            pat = ':' + pat
        return pat

    @property
    def cache_folder(self):
        """
        folder to save previous https request data
        """
        return self.config['DEFAULT']['cache_folder']

    @property
    def instance_base(self):
        """
        vsts instance basically servername.visualstudio.com
        """
        base = self.config['DEFAULT']['vsts_instance_base']
        if base.startswith("http"):
            message = "Please remove http or https from project_whitelist in the config file. Example: mycompany.visualstudio.com"
            raise ValueError(message)
        return base

    @property
    def cache_prefix(self):
        """
        makes cache filenames shorter to reduce issues with path limits
        """
        return self.config['DEFAULT']['cache_file_prefix']

    @property
    def instance(self):
        """
        basically the base url for VSTS
        :returns: url string
        """
        return "https://" + self.instance_base

    @property
    def headers(self):
        """
        :returns: string
        """
        info = self.get_request_settings()
        return info.get("headers")

    @property
    def load_from_source(self):
        """
        Override so it will not get data from a cached file.

        :returns: bool
        """
        return self._load_from_source

    @property
    def api_version(self):
        """
        VSTS API version, if this changes, then there is other work to do
        in this application for successful data extraction.
        So no point putting in a config
        """
        return "3.0"

    @load_from_source.setter
    def load_from_source(self, value):
        self._load_from_source = value

    def get_request_headers(self):
        """
        Sets the Content-type and sets the Authorization header
        :return: object
            http request headers
        """
        headers_req = {}
        headers_req['Content-type'] = "application/json"
        headers_req['Authorization'] = b'Basic' + base64.b64encode(self.personal_access_token.encode('utf-8'))
        return headers_req

    def get_request_settings(self):
        """
        This should go away, and instead properties of this class should be used.
        :return: object
            object with basic information needed for most requests
        todo:phase out using this and use direct properties instead
        """
        request_info = {}
        request_info["instance"] = self.instance
        request_info["api_version"] = self.api_version
        # TODO Try to work project_name out of this class
        request_info["project_name"] = str(self.project_name)
        request_info["headers"] = self.get_request_headers()
        return request_info

    def make_request(self, url, write_to_file=True):
        '''
        Make the VSTS call or gets data from cache, then convert results to a dictionary.
        '''
        print(url)
        file_name = self.build_file_name(url)
        data = {}
        if self._load_from_source:
            data = self.get_data_from_vsts(url, self.crawl_throttle)
        else:
            data = self.get_data_from_file(file_name)

        #if we loaded from source and data is none hitting again does nothing
        if (data is None) and (not self._load_from_source):
            print("     Source: VSTS")
            data = self.get_data_from_vsts(url, self.crawl_throttle)
            #only write to file if we get data from vsts
            if write_to_file:
                self.write_data(url, data)
        return data

    def get_data_from_vsts(self, url, throttle):
        """
        gets data from vsts using provided url
        """
        time.sleep(throttle)
        request = urllib.request.Request(url, headers=self.get_request_headers())
        opener = urllib.request.build_opener()
        response = opener.open(request)
        data = json.loads(response.read())
        return data

    def get_data_from_file(self, file_name):
        """
        if data is in a file don't hit vsts
        """
        try:
            if os.path.isfile(file_name):
                print("     source: cache")
                with open(file_name, 'r') as data_file:
                    data_str = data_file.read().replace('\n', '').replace('\t', '')
                    data = json.loads(data_str)
                    return data
        except:
            print("bury the exception, its ok because we will just get data from vsts")


    def build_file_name(self, url):
        """
        make savable filenames, for local cache
        :returns: string
        """
        file_name = url.replace("https://", '')
        file_name = file_name.replace(self.instance_base, self.cache_prefix)
        file_name = file_name.replace("?", "(qm)") ##doubt any urls wil have qm in them.
        file_name = file_name.replace("/", ".") #needs to be last
        result = os.path.join(self.cache_folder, file_name + ".json")
        return result

    def write_data(self, url, data):
        """
        Writes the http results to a file so we don't have to hit sever to re-run later
        """
        if data is not None:
            file_name = self.build_file_name(url)
            str_json = json.dumps(data)
            print("     Writing File " + file_name)

            with open(file_name, 'w') as file:
                file.write(str_json + '\n')
        else:
            print("    No data to write")
