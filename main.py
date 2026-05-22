from snpx_client.snpx_client import SnpxClient


def main():
    client = SnpxClient("10.227.110.30", connect_on_init=True)
    print("Connected")
    # test
    j= client.j_pos.read()
    x= client.cart_pos.read()
    x1 = client.po
    # end
    client.disconnect()
    print("Disconnected")


if __name__ == "__main__":
    main()
