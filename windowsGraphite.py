# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# For more information on the WMI library see http://msdn.microsoft.com/en-us/library/aa394554%28v=vs.85%29.aspx

import wmi, time, socket

# Returns the location based on the hostname, if the location cant be derived from the hostname choose newton
def findLocation(hostName):
    try:
        # Even number host is watertown
        if int(hostName[-1]) % 2 == 0:
            location = "10.200.1.95"
        # Odd is newton
        else:
            location = "10.70.1.96"
    except ValueError:
        location = "10.70.1.96"
    return location

# Returns the percentage of disk space used and free megabytes for each drive
def checkDisks(wmiInterface):
    data = []
    for disk in wmiInterface.Win32_LogicalDisk (DriveType=3):
        usedBytes = (int(disk.Size) - int(disk.FreeSpace))
        totalSize = int(disk.Size)
        percentUsed = int(float(usedBytes)/float(totalSize)*100)
        data.append(["Disk.Drive_" + disk.Caption + ".percentUsed ", percentUsed])
        data.append(["Disk.Drive_" + disk.Caption + ".freeMegaBytes ", str(float(disk.freeSpace)/1024/1024)])
    return data

# Returns percent usage of each cpu
def checkCPU(wmiInterface):
    data = []
    for cpu in wmiInterface.Win32_PerfFormattedData_PerfOS_Processor():
        data.append(["CPU.Core_" + cpu.Name + ".percentUsed ", cpu.PercentProcessorTime])
    return data

# Returns the percetage of memory used
def checkMemory(wmiInterface):
    data = []
    totalMemory = int(wmiInterface.Win32_ComputerSystem()[0].TotalPhysicalMemory)
    freeMemory =  int (wmiInterface.Win32_OperatingSystem()[0].FreePhysicalMemory)
    usedMemory = totalMemory - freeMemory
    percentUsed = int(float(usedMemory)/float(totalMemory)*100)
    data.append(["Memory.percentUsed ", percentUsed])
    return data

# Returns network performace data
# This is not as simple or intuitive as the others. Why? Because Windows.
# Bytes = (firstReading - lastReading)/timeOfFirstReading - timeOfSecondReading
def checkNetworkSpeed(wmiInterface):
    data = []
    index = 0
    nics = wmiInterface.Win32_PerfRawData_Tcpip_NetworkInterface()
    startTime = time.time()
    for nic in nics:
        if nic.BytesReceivedPerSec != "0" and nic.BytesSentPerSec != "0":
            data.append(["NIC." + nic.Name.replace(" ", "_") + ".kiloBytesReceivedPerSec ", nic.BytesReceivedPerSec])
            data.append(["NIC." + nic.Name.replace(" ","_") + ".kiloBytesSentPerSec ", nic.BytesSentPerSec])
    nics = wmiInterface.Win32_PerfRawData_Tcpip_NetworkInterface()
    time.sleep(1)
    endTime = time.time()
    deltaTime = endTime - startTime
    for nic in nics:
        if nic.BytesReceivedPerSec != "0" and nic.BytesSentPerSec != "0":
            bytesReceived = nic.BytesReceivedPerSec
            bytesSent = nic.BytesSentPerSec
            deltaReceived = int(bytesReceived) - int(data[index][1])
            finalReceivedValue = deltaReceived/deltaTime/1024
            data[index].insert(1,str(finalReceivedValue))
            index = index + 1
            deltaSent = int(bytesSent) - int(data[index][1])
            finalSentValue =deltaSent/deltaTime/1024
            data[index].insert(1,str(finalSentValue))
            index = index + 1
    return data

# Returns the amount of network connections
def checkNetworkConnections(wmiInterface):
    data = []
    connections = wmiInterface.Win32_PerfRawData_Tcpip_TCPv4()
    failures = connections[0].ConnectionFailures
    active = connections[0].ConnectionsActive
    established = connections[0].ConnectionsEstablished
    resets = connections[0].ConnectionsReset
    data.append(["TCPv4Connections.Failures ", failures])
    data.append(["TCPv4Connections.Active ", active])
    data.append(["TCPv4Connections.Established ", established])
    data.append(["TCPv4Connections.Resets ", resets])
    return data

# Formats the data for carbon
def formatData(hostName, timeStamp, data):
    formattedData = ""
    for resourceType in data:
        for resource in resourceType:
            formattedData = formattedData + "servers." + hostName + "." + resource[0] + str(resource[1]) + " " + str(timeStamp) + "\n" 
    return formattedData

# Sends the data to graphite
def sendData(formattedData, location):
    socketInstance = socket.socket()
    socketInstance.connect((location, 2003))
    socketInstance.sendall(formattedData)
    socketInstance.close()
    
def main():
    # Initialize the WMI object, get the hostname, get the timestamp, derive the location
    wmiInterface = wmi.WMI ()
    hostName = wmiInterface.Win32_ComputerSystem()[0].Name.lower()
    timeStamp = str(int(time.time()))
    data = []
    location = findLocation(hostName)

    # Collect the data
    data.append(checkDisks(wmiInterface))
    data.append(checkCPU(wmiInterface))
    data.append(checkMemory(wmiInterface))
    data.append(checkNetworkSpeed(wmiInterface))
    data.append(checkNetworkConnections(wmiInterface))

    # Format the data for carbon
    formattedData = formatData(hostName, timeStamp, data)

    # Send the data to the graphite server 
    sendData(formattedData, location)

if __name__ == '__main__':
    main()
    
