import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { 
  Database, 
  TrendingUp, 
  Shield, 
  Clock, 
  DollarSign, 
  CheckCircle, 
  XCircle,
  AlertTriangle,
  RefreshCw,
  Eye,
  Users
} from 'lucide-react';

interface Oracle {
  address: string;
  name: string;
  reputation: number;
  fee: number;
  isActive: boolean;
  supportedDataTypes: string[];
  totalRequests: number;
  successfulRequests: number;
  successRate: number;
  lastUpdate: number;
}

interface DataRequest {
  id: number;
  requester: string;
  dataType: string;
  deadline: number;
  bounty: number;
  minReputation: number;
  fulfilled: boolean;
  responseTime?: number;
  dataHash?: string;
  selectedOracle?: string;
}

interface ValidationReport {
  requestId: number;
  validator: string;
  isValid: boolean;
  reason: string;
  timestamp: number;
  confidenceScore: number;
}

const OracleInterface: React.FC = () => {
  const [oracles, setOracles] = useState<Oracle[]>([]);
  const [dataRequests, setDataRequests] = useState<DataRequest[]>([]);
  const [validationReports, setValidationReports] = useState<ValidationReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedOracle, setSelectedOracle] = useState<Oracle | null>(null);
  const [activeTab, setActiveTab] = useState('overview');

  // Form states
  const [newOracle, setNewOracle] = useState({
    name: '',
    fee: '',
    supportedDataTypes: [] as string[]
  });
  const [newRequest, setNewRequest] = useState({
    dataType: '',
    deadline: '',
    bounty: '',
    minReputation: ''
  });
  const [validationData, setValidationData] = useState({
    requestId: '',
    isValid: true,
    reason: ''
  });

  // Mock data for demonstration
  useEffect(() => {
    const mockOracles: Oracle[] = [
      {
        address: '0x1234...5678',
        name: 'PriceOracle Pro',
        reputation: 95,
        fee: 0.01,
        isActive: true,
        supportedDataTypes: ['price', 'market_data'],
        totalRequests: 150,
        successfulRequests: 142,
        successRate: 94.7,
        lastUpdate: Date.now() - 3600000
      },
      {
        address: '0xabcd...efgh',
        name: 'WeatherData Hub',
        reputation: 88,
        fee: 0.005,
        isActive: true,
        supportedDataTypes: ['weather', 'environmental'],
        totalRequests: 89,
        successfulRequests: 85,
        successRate: 95.5,
        lastUpdate: Date.now() - 7200000
      },
      {
        address: '0x9876...5432',
        name: 'FoodQuality Validator',
        reputation: 92,
        fee: 0.015,
        isActive: true,
        supportedDataTypes: ['food_quality', 'safety'],
        totalRequests: 203,
        successfulRequests: 198,
        successRate: 97.5,
        lastUpdate: Date.now() - 1800000
      }
    ];

    const mockRequests: DataRequest[] = [
      {
        id: 1,
        requester: '0x1111...2222',
        dataType: 'price',
        deadline: Date.now() + 86400000,
        bounty: 0.1,
        minReputation: 80,
        fulfilled: true,
        responseTime: Date.now() - 3600000,
        dataHash: '0xabc123...',
        selectedOracle: '0x1234...5678'
      },
      {
        id: 2,
        requester: '0x3333...4444',
        dataType: 'weather',
        deadline: Date.now() + 172800000,
        bounty: 0.05,
        minReputation: 70,
        fulfilled: false
      }
    ];

    const mockValidations: ValidationReport[] = [
      {
        requestId: 1,
        validator: '0x5555...6666',
        isValid: true,
        reason: 'Data matches external sources within 2% tolerance',
        timestamp: Date.now() - 3000000,
        confidenceScore: 0.95
      }
    ];

    setOracles(mockOracles);
    setDataRequests(mockRequests);
    setValidationReports(mockValidations);
  }, []);

  const handleRegisterOracle = async () => {
    setLoading(true);
    setError(null);

    try {
      // Mock oracle registration
      const newOracleData: Oracle = {
        address: `0x${Math.random().toString(36).substring(2, 10)}...${Math.random().toString(36).substring(2, 10)}`,
        name: newOracle.name,
        reputation: 100,
        fee: parseFloat(newOracle.fee),
        isActive: true,
        supportedDataTypes: newOracle.supportedDataTypes,
        totalRequests: 0,
        successfulRequests: 0,
        successRate: 100,
        lastUpdate: Date.now()
      };

      setOracles([...oracles, newOracleData]);
      setNewOracle({ name: '', fee: '', supportedDataTypes: [] });
      
    } catch (err) {
      setError('Failed to register oracle');
    } finally {
      setLoading(false);
    }
  };

  const handleRequestData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Mock data request
      const newRequestData: DataRequest = {
        id: dataRequests.length + 1,
        requester: '0xcurrent...user',
        dataType: newRequest.dataType,
        deadline: Date.now() + parseInt(newRequest.deadline) * 1000,
        bounty: parseFloat(newRequest.bounty),
        minReputation: parseInt(newRequest.minReputation),
        fulfilled: false
      };

      setDataRequests([...dataRequests, newRequestData]);
      setNewRequest({ dataType: '', deadline: '', bounty: '', minReputation: '' });
      
    } catch (err) {
      setError('Failed to request data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitValidation = async () => {
    setLoading(true);
    setError(null);

    try {
      // Mock validation submission
      const newValidation: ValidationReport = {
        requestId: parseInt(validationData.requestId),
        validator: '0xcurrent...user',
        isValid: validationData.isValid,
        reason: validationData.reason,
        timestamp: Date.now(),
        confidenceScore: Math.random() * 0.3 + 0.7
      };

      setValidationReports([...validationReports, newValidation]);
      setValidationData({ requestId: '', isValid: true, reason: '' });
      
    } catch (err) {
      setError('Failed to submit validation');
    } finally {
      setLoading(false);
    }
  };

  const getReputationColor = (reputation: number) => {
    if (reputation >= 90) return 'bg-green-500';
    if (reputation >= 70) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getStatusBadge = (isActive: boolean) => (
    <Badge variant={isActive ? 'default' : 'destructive'}>
      {isActive ? 'Active' : 'Inactive'}
    </Badge>
  );

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatAddress = (address: string) => {
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Database className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold">Advanced Oracle System</h1>
        </div>
        <Button variant="outline" onClick={() => window.location.reload()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="oracles">Oracles</TabsTrigger>
          <TabsTrigger value="requests">Data Requests</TabsTrigger>
          <TabsTrigger value="validation">Validation</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Oracles</CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{oracles.length}</div>
                <p className="text-xs text-muted-foreground">
                  {oracles.filter(o => o.isActive).length} active
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Pending Requests</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {dataRequests.filter(r => !r.fulfilled).length}
                </div>
                <p className="text-xs text-muted-foreground">
                  {dataRequests.length} total requests
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Reputation</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {oracles.length > 0 
                    ? (oracles.reduce((sum, o) => sum + o.reputation, 0) / oracles.length).toFixed(1)
                    : '0'
                  }
                </div>
                <p className="text-xs text-muted-foreground">System average</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
                <CheckCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {dataRequests.length > 0
                    ? ((dataRequests.filter(r => r.fulfilled).length / dataRequests.length) * 100).toFixed(1)
                    : '0'
                  }%
                </div>
                <p className="text-xs text-muted-foreground">Request fulfillment</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {dataRequests.slice(0, 5).map(request => (
                  <div key={request.id} className="flex items-center justify-between p-3 border rounded">
                    <div className="flex items-center space-x-3">
                      <Badge variant={request.fulfilled ? 'default' : 'secondary'}>
                        {request.fulfilled ? 'Fulfilled' : 'Pending'}
                      </Badge>
                      <div>
                        <p className="font-medium">Request #{request.id}</p>
                        <p className="text-sm text-muted-foreground">{request.dataType}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">{request.bounty} ETH</p>
                      <p className="text-xs text-muted-foreground">
                        {formatTimestamp(request.deadline)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="oracles" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Oracle Providers</h2>
            <Dialog>
              <DialogTrigger asChild>
                <Button>
                  <Users className="h-4 w-4 mr-2" />
                  Register Oracle
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Register New Oracle</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="name" className="text-right">Name</Label>
                    <Input
                      id="name"
                      value={newOracle.name}
                      onChange={(e) => setNewOracle({ ...newOracle, name: e.target.value })}
                      className="col-span-3"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="fee" className="text-right">Fee (ETH)</Label>
                    <Input
                      id="fee"
                      type="number"
                      step="0.001"
                      value={newOracle.fee}
                      onChange={(e) => setNewOracle({ ...newOracle, fee: e.target.value })}
                      className="col-span-3"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="dataTypes" className="text-right">Data Types</Label>
                    <Input
                      id="dataTypes"
                      placeholder="price,weather,market_data"
                      value={newOracle.supportedDataTypes.join(',')}
                      onChange={(e) => setNewOracle({ 
                        ...newOracle, 
                        supportedDataTypes: e.target.value.split(',').map(s => s.trim()).filter(s => s)
                      })}
                      className="col-span-3"
                    />
                  </div>
                </div>
                <Button onClick={handleRegisterOracle} disabled={loading}>
                  {loading ? 'Registering...' : 'Register Oracle'}
                </Button>
              </DialogContent>
            </Dialog>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {oracles.map((oracle) => (
              <Card key={oracle.address} className="cursor-pointer hover:shadow-lg transition-shadow"
                    onClick={() => setSelectedOracle(oracle)}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-lg">{oracle.name}</CardTitle>
                      <p className="text-sm text-muted-foreground">{formatAddress(oracle.address)}</p>
                    </div>
                    {getStatusBadge(oracle.isActive)}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Reputation</span>
                      <span className="font-medium">{oracle.reputation}</span>
                    </div>
                    <Progress value={oracle.reputation} className="h-2" />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Fee</p>
                      <p className="font-medium">{oracle.fee} ETH</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Success Rate</p>
                      <p className="font-medium">{oracle.successRate}%</p>
                    </div>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Supported Data Types</p>
                    <div className="flex flex-wrap gap-1">
                      {oracle.supportedDataTypes.map((type) => (
                        <Badge key={type} variant="outline" className="text-xs">
                          {type}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <div className="text-xs text-muted-foreground">
                    <p>{oracle.totalRequests} requests • {oracle.successfulRequests} successful</p>
                    <p>Last update: {formatTimestamp(oracle.lastUpdate)}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="requests" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Data Requests</h2>
            <Dialog>
              <DialogTrigger asChild>
                <Button>
                  <Database className="h-4 w-4 mr-2" />
                  Request Data
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Request Data</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="dataType" className="text-right">Data Type</Label>
                    <Select value={newRequest.dataType} 
                            onValueChange={(value) => setNewRequest({ ...newRequest, dataType: value })}>
                      <SelectTrigger className="col-span-3">
                        <SelectValue placeholder="Select data type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="price">Price Data</SelectItem>
                        <SelectItem value="weather">Weather Data</SelectItem>
                        <SelectItem value="food_quality">Food Quality</SelectItem>
                        <SelectItem value="market_data">Market Data</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="deadline" className="text-right">Deadline (hours)</Label>
                    <Input
                      id="deadline"
                      type="number"
                      value={newRequest.deadline}
                      onChange={(e) => setNewRequest({ ...newRequest, deadline: e.target.value })}
                      className="col-span-3"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="bounty" className="text-right">Bounty (ETH)</Label>
                    <Input
                      id="bounty"
                      type="number"
                      step="0.001"
                      value={newRequest.bounty}
                      onChange={(e) => setNewRequest({ ...newRequest, bounty: e.target.value })}
                      className="col-span-3"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="minReputation" className="text-right">Min Reputation</Label>
                    <Input
                      id="minReputation"
                      type="number"
                      value={newRequest.minReputation}
                      onChange={(e) => setNewRequest({ ...newRequest, minReputation: e.target.value })}
                      className="col-span-3"
                    />
                  </div>
                </div>
                <Button onClick={handleRequestData} disabled={loading}>
                  {loading ? 'Requesting...' : 'Request Data'}
                </Button>
              </DialogContent>
            </Dialog>
          </div>

          <div className="space-y-4">
            {dataRequests.map((request) => (
              <Card key={request.id}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-lg">Request #{request.id}</CardTitle>
                      <p className="text-sm text-muted-foreground">
                        Requester: {formatAddress(request.requester)}
                      </p>
                    </div>
                    <Badge variant={request.fulfilled ? 'default' : 'secondary'}>
                      {request.fulfilled ? 'Fulfilled' : 'Pending'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Data Type</p>
                      <p className="font-medium">{request.dataType}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Bounty</p>
                      <p className="font-medium">{request.bounty} ETH</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Deadline</p>
                      <p className="font-medium">{formatTimestamp(request.deadline)}</p>
                    </div>
                  </div>
                  
                  {request.fulfilled && (
                    <div className="mt-4 p-3 bg-green-50 rounded border">
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <span className="text-sm text-green-800">
                          Fulfilled by {formatAddress(request.selectedOracle || '')}
                        </span>
                      </div>
                      {request.responseTime && (
                        <p className="text-xs text-green-600 mt-1">
                          Response time: {formatTimestamp(request.responseTime)}
                        </p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="validation" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Validation Reports</h2>
            <Dialog>
              <DialogTrigger asChild>
                <Button>
                  <Shield className="h-4 w-4 mr-2" />
                  Submit Validation
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Submit Validation</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="requestId" className="text-right">Request ID</Label>
                    <Input
                      id="requestId"
                      type="number"
                      value={validationData.requestId}
                      onChange={(e) => setValidationData({ ...validationData, requestId: e.target.value })}
                      className="col-span-3"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label className="text-right">Valid</Label>
                    <Select value={validationData.isValid.toString()} 
                            onValueChange={(value) => setValidationData({ ...validationData, isValid: value === 'true' })}>
                      <SelectTrigger className="col-span-3">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="true">Valid</SelectItem>
                        <SelectItem value="false">Invalid</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="reason" className="text-right">Reason</Label>
                    <Textarea
                      id="reason"
                      value={validationData.reason}
                      onChange={(e) => setValidationData({ ...validationData, reason: e.target.value })}
                      className="col-span-3"
                      placeholder="Explain your validation decision..."
                    />
                  </div>
                </div>
                <Button onClick={handleSubmitValidation} disabled={loading}>
                  {loading ? 'Submitting...' : 'Submit Validation'}
                </Button>
              </DialogContent>
            </Dialog>
          </div>

          <div className="space-y-4">
            {validationReports.map((report, index) => (
              <Card key={index}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-lg">Request #{report.requestId}</CardTitle>
                      <p className="text-sm text-muted-foreground">
                        Validator: {formatAddress(report.validator)}
                      </p>
                    </div>
                    <Badge variant={report.isValid ? 'default' : 'destructive'}>
                      {report.isValid ? 'Valid' : 'Invalid'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm text-muted-foreground">Reason</p>
                      <p className="text-sm">{report.reason}</p>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-muted-foreground">Confidence Score</p>
                        <div className="flex items-center space-x-2">
                          <Progress value={report.confidenceScore * 100} className="h-2 flex-1" />
                          <span className="text-sm font-medium">{(report.confidenceScore * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Timestamp</p>
                        <p className="text-sm">{formatTimestamp(report.timestamp)}</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {selectedOracle && (
        <Dialog open={!!selectedOracle} onOpenChange={() => setSelectedOracle(null)}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>{selectedOracle.name} - Details</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Address</p>
                  <p className="font-mono text-sm">{selectedOracle.address}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  {getStatusBadge(selectedOracle.isActive)}
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm">Reputation Score</span>
                  <span className="font-medium">{selectedOracle.reputation}/100</span>
                </div>
                <Progress value={selectedOracle.reputation} className="h-2" />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Total Requests</p>
                  <p className="font-medium">{selectedOracle.totalRequests}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Successful</p>
                  <p className="font-medium">{selectedOracle.successfulRequests}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Success Rate</p>
                  <p className="font-medium">{selectedOracle.successRate}%</p>
                </div>
              </div>

              <div>
                <p className="text-sm text-muted-foreground mb-2">Supported Data Types</p>
                <div className="flex flex-wrap gap-2">
                  {selectedOracle.supportedDataTypes.map((type) => (
                    <Badge key={type} variant="outline">
                      {type}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Service Fee</p>
                  <p className="font-medium">{selectedOracle.fee} ETH per request</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Last Update</p>
                  <p className="font-medium">{formatTimestamp(selectedOracle.lastUpdate)}</p>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default OracleInterface;
