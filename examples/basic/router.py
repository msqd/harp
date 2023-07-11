from harp import Harp

proxy = Harp()

proxy.mount('/bin/', 'http://localhost:8080/')

if __name__ == '__main__':
    proxy.run()

