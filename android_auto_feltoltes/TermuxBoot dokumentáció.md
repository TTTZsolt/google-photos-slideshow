The Termux:Boot add-on provides functionality to run programs under Termux when the device boots up.

Usage
Start the Termux:Boot app once to allow the system to start the app at boot time.
Create the ~/.termux/boot/ directory.
Put scripts you want to execute inside the ~/.termux/boot/ directory.
If there are multiple files, they will be executed in a sorted order.
Note that you may want to run termux-wake-lock as first thing if you want to ensure that the device is prevented from sleeping.
Example
To start an sshd server and prevent the device from sleeping at boot, create a file at ~/.termux/boot/start-sshd containing the three lines

    #!/data/data/com.termux/files/usr/bin/sh
    termux-wake-lock
    sshd
Learn more
Join the Termux community through the various channels listed at https://termux.org/community

Report issues
https://github.com/termux/termux-boot/issues

