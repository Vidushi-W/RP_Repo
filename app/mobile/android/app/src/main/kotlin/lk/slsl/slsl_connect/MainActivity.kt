package lk.slsl.slsl_connect

import android.Manifest
import android.bluetooth.*
import android.bluetooth.le.*
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val handler = Handler(Looper.getMainLooper())
    private var pending: MethodChannel.Result? = null
    private var gatt: BluetoothGatt? = null
    private var scan: ScanCallback? = null
    private val manager get() = getSystemService(BLUETOOTH_SERVICE) as BluetoothManager
    override fun configureFlutterEngine(engine: FlutterEngine) {
        super.configureFlutterEngine(engine)
        MethodChannel(engine.dartExecutor.binaryMessenger,"lk.slsl/connect/gloves").setMethodCallHandler { call,result ->
            when(call.method) {
                "scan" -> {
                    if(pending!=null) result.error("BUSY","A Bluetooth request is running.",null)
                    else {
                        pending=result
                        val permissions=if(Build.VERSION.SDK_INT>=31) arrayOf(Manifest.permission.BLUETOOTH_SCAN,Manifest.permission.BLUETOOTH_CONNECT) else arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
                        if(permissions.any { checkSelfPermission(it)!=PackageManager.PERMISSION_GRANTED }) requestPermissions(permissions,403)
                        else startScan()
                    }
                }
                "connect" -> {
                    if(pending!=null) result.error("BUSY","A Bluetooth request is running.",null)
                    else try {
                        val id=call.argument<String>("id")!!
                        val device=manager.adapter.getRemoteDevice(id)
                        gatt?.close();pending=result
                        gatt=device.connectGatt(this,false,object: BluetoothGattCallback(){
                            override fun onConnectionStateChange(deviceGatt:BluetoothGatt,status:Int,state:Int){
                                handler.post {
                                    if(state==BluetoothProfile.STATE_CONNECTED && status==BluetoothGatt.GATT_SUCCESS){pending?.success(null);pending=null}
                                    else if(state==BluetoothProfile.STATE_DISCONNECTED){pending?.error("DISCONNECTED","Device disconnected.",null);pending=null;deviceGatt.close()}
                                }
                            }
                        },BluetoothDevice.TRANSPORT_LE)
                        handler.postDelayed({if(pending===result){pending=null;gatt?.disconnect();gatt?.close();gatt=null;result.error("TIMEOUT","Device did not connect.",null)}},12000)
                    }catch(e:Exception){pending=null;result.error("BLUETOOTH",e.message,null)}
                }
                "disconnect" -> {try{gatt?.disconnect();gatt?.close();gatt=null;result.success(null)}catch(e:Exception){result.error("BLUETOOTH",e.message,null)}}
                else -> result.notImplemented()
            }
        }
    }
    override fun onRequestPermissionsResult(code:Int,permissions:Array<out String>,grants:IntArray){
        super.onRequestPermissionsResult(code,permissions,grants)
        if(code==403){if(grants.isNotEmpty()&&grants.all{it==PackageManager.PERMISSION_GRANTED})startScan() else{pending?.error("PERMISSION","Bluetooth permission is required.",null);pending=null}}
    }
    private fun startScan(){
        val result=pending?:return
        try{
            val adapter=manager.adapter
            if(adapter==null||!adapter.isEnabled){pending=null;result.error("UNAVAILABLE","Enable Bluetooth on a physical phone.",null);return}
            val scanner=adapter.bluetoothLeScanner
            val found=linkedMapOf<String,Map<String,Any>>()
            val callback=object:ScanCallback(){
                override fun onScanResult(type:Int,entry:ScanResult){
                    found[entry.device.address]=mapOf("id" to entry.device.address,"name" to (entry.scanRecord?.deviceName?:entry.device.name?:"Unnamed device"),"rssi" to entry.rssi)
                }
                override fun onScanFailed(code:Int){handler.post{if(pending===result){pending=null;result.error("SCAN","Bluetooth scan failed ($code).",null)}}}
            }
            scan=callback;scanner.startScan(callback)
            handler.postDelayed({scanner.stopScan(callback);scan=null;if(pending===result){pending=null;result.success(found.values.toList())}},8000)
        }catch(e:Exception){pending=null;result.error("BLUETOOTH",e.message,null)}
    }
    override fun onDestroy(){
        try{scan?.let{manager.adapter?.bluetoothLeScanner?.stopScan(it)};gatt?.close()}catch(_:Exception){}
        handler.removeCallbacksAndMessages(null);pending?.error("CLOSED","Bluetooth screen closed.",null);pending=null
        super.onDestroy()
    }
}
