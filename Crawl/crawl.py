import os
import requests
import shutil
from multiprocessing import Pool
import argparse
from collect_links import CollectLinks
from catagories import dict_categories
import imghdr
import base64

class Sites:
    GOOGLE = 1
    NAVER = 2
    GOOGLE_FULL = 3
    NAVER_FULL = 4

    @staticmethod
    def get_text(code):
        if code == Sites.GOOGLE:
            return 'google'
        elif code == Sites.NAVER:
            return 'naver'
        elif code == Sites.GOOGLE_FULL:
            return 'google'
        elif code == Sites.NAVER_FULL:
            return 'naver'

    @staticmethod
    def get_face_url(code):
        if code == Sites.GOOGLE or Sites.GOOGLE_FULL:
            return "&tbs=itp:face"
        if code == Sites.NAVER or Sites.NAVER_FULL:
            return "&face=1"


class AutoCrawler:
    def __init__(self, skip_already_exist=True, n_threads=4, do_google=True, do_naver=True, download_path='data',
                 full_resolution=False, face=False):
        """
        :param skip_already_exist: Skips keyword already downloaded before. This is needed when re-downloading.
        :param n_threads: Number of threads to download.
        :param do_google: Download from google.com (boolean)
        :param do_naver: Download from naver.com (boolean)
        :param download_path: Download folder path
        :param full_resolution: Download full resolution image instead of thumbnails (slow)
        :param face: Face search mode
        """

        self.skip = skip_already_exist
        self.n_threads = n_threads
        self.do_google = do_google
        self.do_naver = do_naver
        self.download_path = download_path
        self.full_resolution = full_resolution
        self.face = face

        os.makedirs('./{}'.format(self.download_path), exist_ok=True)

    @staticmethod
    def all_dirs(path):
        paths = []
        for dir in os.listdir(path):
            if os.path.isdir(path + '/' + dir):
                paths.append(path + '/' + dir)

        return paths

    @staticmethod
    def all_files(path):
        paths = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if os.path.isfile(path + '/' + file):
                    paths.append(path + '/' + file)

        return paths

    @staticmethod
    def get_extension_from_link(link, default='jpg'):
        splits = str(link).split('.')
        if len(splits) == 0:
            return default
        ext = splits[-1].lower()
        if ext == 'jpg' or ext == 'jpeg':
            return 'jpg'
        elif ext == 'gif':
            return 'gif'
        elif ext == 'png':
            return 'png'
        else:
            return default

    @staticmethod
    def validate_image(path):
        ext = imghdr.what(path)
        if ext == 'jpeg':
            ext = 'jpg'
        return ext  # returns None if not valid

    @staticmethod
    def make_dir(dirname):
        current_path = os.getcwd()
        path = os.path.join(current_path, dirname)
        if not os.path.exists(path):
            os.makedirs(path)

    # @staticmethod
    # def get_keywords(keywords_file='keywords.txt'):
    #     # read search keywords from file
    #     with open(keywords_file, 'r', encoding='utf-8-sig') as f:
    #         text = f.read()
    #         lines = text.split('\n')
    #         lines = filter(lambda x: x != '' and x is not None, lines)
    #         keywords = sorted(set(lines))

    #     print('{} keywords found: {}'.format(len(keywords), keywords))

    #     # re-save sorted keywords
    #     with open(keywords_file, 'w+', encoding='utf-8') as f:
    #         for keyword in keywords:
    #             f.write('{}\n'.format(keyword))

    #     return keywords

    @staticmethod
    def save_object_to_file(object, file_path, is_base64=False):
        try:
            with open('{}'.format(file_path), 'wb') as file:
                if is_base64:
                    file.write(object)
                else:
                    shutil.copyfileobj(object.raw, file)
        except Exception as e:
            print('Save failed - {}'.format(e))

    @staticmethod
    def base64_to_object(src):
        header, encoded = str(src).split(',', 1)
        data = base64.decodebytes(bytes(encoded, encoding='utf-8'))
        return data

    def download_images(self, field_dir, keyword, links, site_name):
        # self.make_dir('{}/{}'.format(self.download_path, keyword))
        total = len(links)

        for index, link in enumerate(links):
            try:
                print('Downloading {} from {}: {} / {}'.format(keyword, site_name, index + 1, total))

                if str(link).startswith('data:image/jpeg;base64'):
                    response = self.base64_to_object(link)
                    ext = 'jpg'
                    is_base64 = True
                elif str(link).startswith('data:image/png;base64'):
                    response = self.base64_to_object(link)
                    ext = 'png'
                    is_base64 = True
                else:
                    response = requests.get(link, stream=True)
                    ext = self.get_extension_from_link(link)
                    is_base64 = False

                no_ext_path = '{}/{}/{}_{}'.format(field_dir, keyword, site_name, str(index).zfill(4))
                path = no_ext_path + '.' + ext
                self.save_object_to_file(response, path, is_base64=is_base64)

                del response

                ext2 = self.validate_image(path)
                if ext2 is None:
                    print('Unreadable file - {}'.format(link))
                    os.remove(path)
                else:
                    if ext != ext2:
                        path2 = no_ext_path + '.' + ext2
                        os.rename(path, path2)
                        print('Renamed extension {} -> {}'.format(ext, ext2))

            except Exception as e:
                print('Download failed - ', e)
                continue

    def download_from_site(self, field_dir, keyword, site_code):
        site_name = Sites.get_text(site_code)
        add_url = Sites.get_face_url(site_code) if self.face else ""

        # try:
        collect = CollectLinks()  # initialize chrome driver
        # except Exception as e:
        #     print('Error occurred while initializing chromedriver - {}'.format(e))
        #     return

        try:
            print('Collecting links... {} from {}'.format(keyword, site_name))

            if site_code == Sites.GOOGLE:
                links = collect.google(keyword, add_url)

            elif site_code == Sites.NAVER:
                links = collect.naver(keyword, add_url)

            elif site_code == Sites.GOOGLE_FULL:
                links = collect.google_full(keyword, add_url)

            elif site_code == Sites.NAVER_FULL:
                links = collect.naver_full(keyword, add_url)

            else:
                print('Invalid Site Code')
                links = []

            print('Downloading images from collected links... {} from {}'.format(keyword, site_name))
            self.download_images(field_dir, keyword, links, site_name)

            print('Done {} : {}'.format(site_name, keyword))

        except Exception as e:
            print('Exception {}:{} - {}'.format(site_name, keyword, e))

    def download(self, args):
        self.download_from_site(field_dir=args[2], keyword=args[0], site_code=args[1])

    def do_crawling(self):
        tasks = []

        for field, list_subfield in dict_categories.items():
            dir_field_name = os.path.join(self.download_path, field)
            if not os.path.exists(dir_field_name):
                os.mkdir(dir_field_name)
            
            for sub_field in list_subfield:
                dir_subfield_name = os.path.join(dir_field_name, sub_field)
                if not os.path.exists(dir_subfield_name):
                    os.mkdir(dir_subfield_name)
                    
                if self.do_google:
                    if self.full_resolution:
                        tasks.append([sub_field, Sites.GOOGLE_FULL, dir_field_name])
                    else:
                        tasks.append([sub_field, Sites.GOOGLE, dir_field_name])

                if self.do_naver:
                    if self.full_resolution:
                        tasks.append([sub_field, Sites.NAVER_FULL, dir_field_name])
                    else:
                        tasks.append([sub_field, Sites.NAVER, dir_field_name])

        pool = Pool(self.n_threads)
        pool.map_async(self.download, tasks)
        pool.close()
        pool.join()
        print('Task ended. Pool join.')
        print('End Program')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip', type=str, default='true',
                        help='Skips keyword already downloaded before. This is needed when re-downloading.')
    parser.add_argument('--threads', type=int, default=4, help='Number of threads to download.')
    parser.add_argument('--google', type=str, default='true', help='Download from google.com (boolean)')
    parser.add_argument('--naver', type=str, default='true', help='Download from naver.com (boolean)')
    parser.add_argument('--full', type=str, default='false', help='Download full resolution image instead of thumbnails (slow)')
    parser.add_argument('--face', type=str, default='false', help='Face search mode')
    args = parser.parse_args()

    _skip = False if str(args.skip).lower() == 'false' else True
    _threads = args.threads
    _google = False if str(args.google).lower() == 'false' else True
    _naver = False if str(args.naver).lower() == 'false' else True
    _full = False if str(args.full).lower() == 'false' else True
    _face = False if str(args.face).lower() == 'false' else True

    print('Options - skip:{}, threads:{}, google:{}, naver:{}, full_resolution:{}, face:{}'.format(_skip, _threads, _google, _naver, _full, _face))

    crawler = AutoCrawler(skip_already_exist=_skip, n_threads=_threads, do_google=_google, do_naver=_naver, full_resolution=_full, face=_face)
    crawler.do_crawling()

# main()
