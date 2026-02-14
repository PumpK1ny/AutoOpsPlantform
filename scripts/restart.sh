echo "重启qq bot..."
systemctl restart auto-fund-qq.service
echo "success!"
echo "重启计划组件"
systemctl restart auto-fund-scheduler.service
echo "success!"
echo "重启web组件"
systemctl restart auto-fund-web.service
echo "success!"
