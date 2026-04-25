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
  Shield, 
  Eye, 
  EyeOff, 
  Lock, 
  Unlock, 
  CheckCircle, 
  XCircle,
  AlertTriangle,
  Clock,
  Zap,
  User,
  CreditCard,
  Award,
  RefreshCw,
  FileText,
  Key
} from 'lucide-react';

interface ZKCircuit {
  name: string;
  description: string;
  creator: string;
  circuitType: string;
  isActive: boolean;
  createdTime: number;
  verificationCount: number;
}

interface ZKProof {
  proofId: string;
  circuitName: string;
  creator: string;
  publicInputs: string[];
  status: string;
  createdTime: number;
  verifiedTime?: number;
  verificationResult?: boolean;
  gasUsed: number;
}

interface VerificationRecord {
  proofHash: string;
  verifier: string;
  timestamp: number;
  isValid: boolean;
  circuitName: string;
  gasUsed: number;
}

const ZKInterface: React.FC = () => {
  const [circuits, setCircuits] = useState<ZKCircuit[]>([]);
  const [proofs, setProofs] = useState<ZKProof[]>([]);
  const [verifications, setVerifications] = useState<VerificationRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCircuit, setSelectedCircuit] = useState<ZKCircuit | null>(null);
  const [activeTab, setActiveTab] = useState('overview');

  // Form states
  const [newCircuit, setNewCircuit] = useState({
    name: '',
    description: '',
    circuitType: ''
  });
  const [proofGeneration, setProofGeneration] = useState({
    circuitName: '',
    privateInputs: '',
    publicInputs: ''
  });
  const [verificationData, setVerificationData] = useState({
    circuitName: '',
    proofData: '',
    publicInputs: ''
  });

  // Mock data for demonstration
  useEffect(() => {
    const mockCircuits: ZKCircuit[] = [
      {
        name: 'age_verification',
        description: 'Verify age without revealing actual age',
        creator: '0x1234...5678',
        circuitType: 'AGE_VERIFICATION',
        isActive: true,
        createdTime: Date.now() - 86400000,
        verificationCount: 245
      },
      {
        name: 'identity_verification',
        description: 'Verify identity without revealing personal data',
        creator: '0xabcd...efgh',
        circuitType: 'IDENTITY_VERIFICATION',
        isActive: true,
        createdTime: Date.now() - 172800000,
        verificationCount: 189
      },
      {
        name: 'financial_verification',
        description: 'Verify financial status without revealing amounts',
        creator: '0x9876...5432',
        circuitType: 'FINANCIAL_VERIFICATION',
        isActive: true,
        createdTime: Date.now() - 259200000,
        verificationCount: 156
      },
      {
        name: 'membership_verification',
        description: 'Verify membership without revealing identity',
        creator: '0x1111...2222',
        circuitType: 'MEMBERSHIP_VERIFICATION',
        isActive: false,
        createdTime: Date.now() - 345600000,
        verificationCount: 67
      }
    ];

    const mockProofs: ZKProof[] = [
      {
        proofId: '0xabc123...',
        circuitName: 'age_verification',
        creator: '0x3333...4444',
        publicInputs: ['age_commitment_123', 'timestamp_123'],
        status: 'verified',
        createdTime: Date.now() - 3600000,
        verifiedTime: Date.now() - 3000000,
        verificationResult: true,
        gasUsed: 125000
      },
      {
        proofId: '0xdef456...',
        circuitName: 'identity_verification',
        creator: '0x5555...6666',
        publicInputs: ['identity_commitment_456', 'nonce_456'],
        status: 'pending',
        createdTime: Date.now() - 1800000,
        gasUsed: 0
      }
    ];

    const mockVerifications: VerificationRecord[] = [
      {
        proofHash: '0xghi789...',
        verifier: '0x7777...8888',
        timestamp: Date.now() - 900000,
        isValid: true,
        circuitName: 'age_verification',
        gasUsed: 118000
      },
      {
        proofHash: '0xjkl012...',
        verifier: '0x9999...0000',
        timestamp: Date.now() - 600000,
        isValid: true,
        circuitName: 'financial_verification',
        gasUsed: 134000
      }
    ];

    setCircuits(mockCircuits);
    setProofs(mockProofs);
    setVerifications(mockVerifications);
  }, []);

  const handleRegisterCircuit = async () => {
    setLoading(true);
    setError(null);

    try {
      // Mock circuit registration
      const newCircuitData: ZKCircuit = {
        name: newCircuit.name,
        description: newCircuit.description,
        creator: '0xcurrent...user',
        circuitType: newCircuit.circuitType,
        isActive: true,
        createdTime: Date.now(),
        verificationCount: 0
      };

      setCircuits([...circuits, newCircuitData]);
      setNewCircuit({ name: '', description: '', circuitType: '' });
      
    } catch (err) {
      setError('Failed to register circuit');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateProof = async () => {
    setLoading(true);
    setError(null);

    try {
      // Mock proof generation
      const newProof: ZKProof = {
        proofId: `0x${Math.random().toString(36).substring(2, 10)}...`,
        circuitName: proofGeneration.circuitName,
        creator: '0xcurrent...user',
        publicInputs: proofGeneration.publicInputs.split(',').map(s => s.trim()),
        status: 'pending',
        createdTime: Date.now(),
        gasUsed: 0
      };

      setProofs([...proofs, newProof]);
      setProofGeneration({ circuitName: '', privateInputs: '', publicInputs: '' });
      
    } catch (err) {
      setError('Failed to generate proof');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyProof = async () => {
    setLoading(true);
    setError(null);

    try {
      // Mock proof verification
      const updatedProofs = proofs.map(proof => {
        if (proof.circuitName === verificationData.circuitName && proof.status === 'pending') {
          return {
            ...proof,
            status: 'verified',
            verifiedTime: Date.now(),
            verificationResult: true,
            gasUsed: 120000 + Math.floor(Math.random() * 30000)
          };
        }
        return proof;
      });

      setProofs(updatedProofs);
      setVerificationData({ circuitName: '', proofData: '', publicInputs: '' });
      
    } catch (err) {
      setError('Failed to verify proof');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'verified':
        return <Badge className="bg-green-500">Verified</Badge>;
      case 'pending':
        return <Badge className="bg-yellow-500">Pending</Badge>;
      case 'rejected':
        return <Badge className="bg-red-500">Rejected</Badge>;
      case 'expired':
        return <Badge className="bg-gray-500">Expired</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getCircuitIcon = (circuitType: string) => {
    switch (circuitType) {
      case 'AGE_VERIFICATION':
        return <User className="h-5 w-5" />;
      case 'IDENTITY_VERIFICATION':
        return <Shield className="h-5 w-5" />;
      case 'FINANCIAL_VERIFICATION':
        return <CreditCard className="h-5 w-5" />;
      case 'MEMBERSHIP_VERIFICATION':
        return <Award className="h-5 w-5" />;
      default:
        return <Key className="h-5 w-5" />;
    }
  };

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatAddress = (address: string) => {
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  };

  const formatGas = (gas: number) => {
    return `${(gas / 1000).toFixed(1)}k`;
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Shield className="h-8 w-8 text-purple-600" />
          <h1 className="text-3xl font-bold">Zero-Knowledge Proofs</h1>
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
          <TabsTrigger value="circuits">Circuits</TabsTrigger>
          <TabsTrigger value="proofs">Proofs</TabsTrigger>
          <TabsTrigger value="verifications">Verifications</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Circuits</CardTitle>
                <Key className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{circuits.length}</div>
                <p className="text-xs text-muted-foreground">
                  {circuits.filter(c => c.isActive).length} active
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Generated Proofs</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{proofs.length}</div>
                <p className="text-xs text-muted-foreground">
                  {proofs.filter(p => p.status === 'verified').length} verified
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
                <CheckCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {proofs.length > 0
                    ? ((proofs.filter(p => p.verificationResult === true).length / proofs.length) * 100).toFixed(1)
                    : '0'
                  }%
                </div>
                <p className="text-xs text-muted-foreground">Verification success</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Gas Used</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {proofs.filter(p => p.gasUsed > 0).length > 0
                    ? formatGas(proofs.filter(p => p.gasUsed > 0).reduce((sum, p) => sum + p.gasUsed, 0) / proofs.filter(p => p.gasUsed > 0).length)
                    : '0'
                  }
                </div>
                <p className="text-xs text-muted-foreground">Per verification</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Privacy Features</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div className="flex items-center space-x-3">
                    <EyeOff className="h-6 w-6 text-blue-600" />
                    <div>
                      <h3 className="font-medium">Private Data Protection</h3>
                      <p className="text-sm text-muted-foreground">Your sensitive data never leaves your device</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <Lock className="h-6 w-6 text-green-600" />
                    <div>
                      <h3 className="font-medium">Cryptographic Security</h3>
                      <p className="text-sm text-muted-foreground">Mathematical proof of validity without disclosure</p>
                    </div>
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="flex items-center space-x-3">
                    <Unlock className="h-6 w-6 text-purple-600" />
                    <div>
                      <h3 className="font-medium">Selective Disclosure</h3>
                      <p className="text-sm text-muted-foreground">Prove only what's necessary</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <CheckCircle className="h-6 w-6 text-orange-600" />
                    <div>
                      <h3 className="font-medium">Instant Verification</h3>
                      <p className="text-sm text-muted-foreground">Verify proofs in milliseconds</p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="circuits" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">ZK Circuits</h2>
            <Dialog>
              <DialogTrigger asChild>
                <Button>
                  <Key className="h-4 w-4 mr-2" />
                  Register Circuit
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Register New Circuit</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="name" className="text-right">Name</Label>
                    <Input
                      id="name"
                      value={newCircuit.name}
                      onChange={(e) => setNewCircuit({ ...newCircuit, name: e.target.value })}
                      className="col-span-3"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="description" className="text-right">Description</Label>
                    <Textarea
                      id="description"
                      value={newCircuit.description}
                      onChange={(e) => setNewCircuit({ ...newCircuit, description: e.target.value })}
                      className="col-span-3"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="circuitType" className="text-right">Type</Label>
                    <Select value={newCircuit.circuitType} 
                            onValueChange={(value) => setNewCircuit({ ...newCircuit, circuitType: value })}>
                      <SelectTrigger className="col-span-3">
                        <SelectValue placeholder="Select circuit type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="AGE_VERIFICATION">Age Verification</SelectItem>
                        <SelectItem value="IDENTITY_VERIFICATION">Identity Verification</SelectItem>
                        <SelectItem value="FINANCIAL_VERIFICATION">Financial Verification</SelectItem>
                        <SelectItem value="MEMBERSHIP_VERIFICATION">Membership Verification</SelectItem>
                        <SelectItem value="QUALIFICATION_VERIFICATION">Qualification Verification</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <Button onClick={handleRegisterCircuit} disabled={loading}>
                  {loading ? 'Registering...' : 'Register Circuit'}
                </Button>
              </DialogContent>
            </Dialog>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {circuits.map((circuit) => (
              <Card key={circuit.name} className="cursor-pointer hover:shadow-lg transition-shadow"
                    onClick={() => setSelectedCircuit(circuit)}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="flex items-center space-x-2">
                      {getCircuitIcon(circuit.circuitType)}
                      <CardTitle className="text-lg">{circuit.name}</CardTitle>
                    </div>
                    <Badge variant={circuit.isActive ? 'default' : 'secondary'}>
                      {circuit.isActive ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground">{circuit.description}</p>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Verifications</p>
                      <p className="font-medium">{circuit.verificationCount}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Created</p>
                      <p className="font-medium">{formatTimestamp(circuit.createdTime)}</p>
                    </div>
                  </div>

                  <div className="text-xs text-muted-foreground">
                    <p>Creator: {formatAddress(circuit.creator)}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="proofs" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Generated Proofs</h2>
            <Dialog>
              <DialogTrigger asChild>
                <Button>
                  <FileText className="h-4 w-4 mr-2" />
                  Generate Proof
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Generate ZK Proof</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="circuitName" className="text-right">Circuit</Label>
                    <Select value={proofGeneration.circuitName} 
                            onValueChange={(value) => setProofGeneration({ ...proofGeneration, circuitName: value })}>
                      <SelectTrigger className="col-span-3">
                        <SelectValue placeholder="Select circuit" />
                      </SelectTrigger>
                      <SelectContent>
                        {circuits.filter(c => c.isActive).map((circuit) => (
                          <SelectItem key={circuit.name} value={circuit.name}>{circuit.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="privateInputs" className="text-right">Private Inputs</Label>
                    <Textarea
                      id="privateInputs"
                      value={proofGeneration.privateInputs}
                      onChange={(e) => setProofGeneration({ ...proofGeneration, privateInputs: e.target.value })}
                      className="col-span-3"
                      placeholder="age:25, name:John"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="publicInputs" className="text-right">Public Inputs</Label>
                    <Textarea
                      id="publicInputs"
                      value={proofGeneration.publicInputs}
                      onChange={(e) => setProofGeneration({ ...proofGeneration, publicInputs: e.target.value })}
                      className="col-span-3"
                      placeholder="commitment_123, timestamp_456"
                    />
                  </div>
                </div>
                <Button onClick={handleGenerateProof} disabled={loading}>
                  {loading ? 'Generating...' : 'Generate Proof'}
                </Button>
              </DialogContent>
            </Dialog>
          </div>

          <div className="space-y-4">
            {proofs.map((proof) => (
              <Card key={proof.proofId}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-lg">Proof {proof.proofId}</CardTitle>
                      <p className="text-sm text-muted-foreground">
                        Circuit: {proof.circuitName} • Creator: {formatAddress(proof.creator)}
                      </p>
                    </div>
                    {getStatusBadge(proof.status)}
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Created</p>
                      <p className="font-medium">{formatTimestamp(proof.createdTime)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Gas Used</p>
                      <p className="font-medium">{formatGas(proof.gasUsed)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Public Inputs</p>
                      <p className="font-medium">{proof.publicInputs.length} inputs</p>
                    </div>
                  </div>
                  
                  {proof.verifiedTime && (
                    <div className="mt-4 p-3 bg-green-50 rounded border">
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <span className="text-sm text-green-800">
                          Verified at {formatTimestamp(proof.verifiedTime)}
                        </span>
                      </div>
                      {proof.verificationResult !== undefined && (
                        <p className="text-xs text-green-600 mt-1">
                          Result: {proof.verificationResult ? 'Valid' : 'Invalid'}
                        </p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="verifications" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Verification Records</h2>
            <Dialog>
              <DialogTrigger asChild>
                <Button>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Verify Proof
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Verify ZK Proof</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="verifyCircuit" className="text-right">Circuit</Label>
                    <Select value={verificationData.circuitName} 
                            onValueChange={(value) => setVerificationData({ ...verificationData, circuitName: value })}>
                      <SelectTrigger className="col-span-3">
                        <SelectValue placeholder="Select circuit" />
                      </SelectTrigger>
                      <SelectContent>
                        {circuits.filter(c => c.isActive).map((circuit) => (
                          <SelectItem key={circuit.name} value={circuit.name}>{circuit.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="proofData" className="text-right">Proof Data</Label>
                    <Textarea
                      id="proofData"
                      value={verificationData.proofData}
                      onChange={(e) => setVerificationData({ ...verificationData, proofData: e.target.value })}
                      className="col-span-3"
                      placeholder="Paste proof data here..."
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="verifyInputs" className="text-right">Public Inputs</Label>
                    <Textarea
                      id="verifyInputs"
                      value={verificationData.publicInputs}
                      onChange={(e) => setVerificationData({ ...verificationData, publicInputs: e.target.value })}
                      className="col-span-3"
                      placeholder="commitment_123, timestamp_456"
                    />
                  </div>
                </div>
                <Button onClick={handleVerifyProof} disabled={loading}>
                  {loading ? 'Verifying...' : 'Verify Proof'}
                </Button>
              </DialogContent>
            </Dialog>
          </div>

          <div className="space-y-4">
            {verifications.map((verification, index) => (
              <Card key={index}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-lg">Verification #{index + 1}</CardTitle>
                      <p className="text-sm text-muted-foreground">
                        Proof: {verification.proofHash} • Verifier: {formatAddress(verification.verifier)}
                      </p>
                    </div>
                    <Badge variant={verification.isValid ? 'default' : 'destructive'}>
                      {verification.isValid ? 'Valid' : 'Invalid'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Circuit</p>
                      <p className="font-medium">{verification.circuitName}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Gas Used</p>
                      <p className="font-medium">{formatGas(verification.gasUsed)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Timestamp</p>
                      <p className="font-medium">{formatTimestamp(verification.timestamp)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {selectedCircuit && (
        <Dialog open={!!selectedCircuit} onOpenChange={() => setSelectedCircuit(null)}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle className="flex items-center space-x-2">
                {getCircuitIcon(selectedCircuit.circuitType)}
                <span>{selectedCircuit.name}</span>
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Description</p>
                <p className="text-sm">{selectedCircuit.description}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <Badge variant={selectedCircuit.isActive ? 'default' : 'secondary'}>
                    {selectedCircuit.isActive ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Type</p>
                  <p className="font-medium">{selectedCircuit.circuitType}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Total Verifications</p>
                  <p className="font-medium">{selectedCircuit.verificationCount}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Created</p>
                  <p className="font-medium">{formatTimestamp(selectedCircuit.createdTime)}</p>
                </div>
              </div>

              <div>
                <p className="text-sm text-muted-foreground">Creator</p>
                <p className="font-mono text-sm">{selectedCircuit.creator}</p>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default ZKInterface;
