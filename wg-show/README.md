```bash
sudo nvim /Library/LaunchDaemons/com.wgshow.plist
# then write the content in the com.wgshow.plist into it

# for autorun
sudo chown root:wheel /Library/LaunchDaemons/com.wireguard.server.plist
sudo launchctl enable system/com.wgshow
sudo launchctl bootstrap system /Library/LaunchDaemons/com.wgshow.plist
```
