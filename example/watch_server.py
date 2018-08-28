import argparse

from train_logger.server.http_server import HTTPServer

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # settings
    parser.add_argument('--log_dir', type=str, default='test_log')
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)

    args = parser.parse_args()

    http_server = HTTPServer(log_dir=args.log_dir, name="watching", bind_host=args.host, bind_port=args.port, quiet=False)
    http_server.start(use_thread=False)
