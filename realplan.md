lets implement this here the source https://link.springer.com/article/10.1186/s42400-024-00226-8  Threshold encryption is an essential tool used to combat collusion attacks. It decentralizes the centralized authority of traditional public key cryptography to avoid the failure or attack of a single point. In a threshold encryption scheme, the key is divided into multiple parts and assigned to several participants. The encryption key is public and can directly encrypt the message, but decryption requires multiple participants to work together to reconstruct the key and decrypt the data. In this paper, we use an ECC-based threshold encryption scheme without a trusted center (Hou et al. 2011), which we adapted for ballots encryption on the blockchain. It can prevent the premature disclosure of intermediate voting results, thus affecting the final voting results. Details of the scheme

The scheme has five stages: Initialization, Registration, Voting Initiation, Voting, and Counting. In the following sections, we will detail each of these stages. Assuming that there are k nodes on the blockchain and CA, C, O have at least one master node. And C has already been elected and can fulfil its responsibilities correctly.
Initialization stage

During the initialization stage, CA first generates the parameters used by each technology, including global public parameters g, p, q, the curve hash function H(x) and curve pairing function e(x,y) associated with blind signatures, as well as the elliptic curve and its base point G associated with threshold encryption.

Then, the master nodes of CA, C, and O generate their respective blind signature key pairs . And send to the smart contract to generate the publicly available blind signature public key bpk.

Finally, all the nodes on the blockchain complete the initialization of threshold encryption in the following steps:

Let be a unique identifier for Node , and the threshold value t = 2k/3. Node chooses a random number as the private key and computes the public key . constructs a t-1 polynomial as in Eq. 7.
(7)

computes and sends it to . When receives from the other n−1 participants and verifies that it passes, it calculates its secret share through Eq. 8. Then, computes and broadcasts .
(8)

Then, ballot encryption public key epk can be calculated by the smart contract according to Eq. 9.
(9)
Registration stage

Voters must register on the blockchain before they can vote, which is necessary to ensure the vote’s legitimacy. To prove their voting eligibility, voters must send their identity information and the public key used for voting to the smart contract to obtain signature authentication. To protect the privacy of voters, ensure the anonymity of voting, and prevent other entities from linking the voting public key with the actual identities of voters, a blind signature technique is needed here. Also, in order to prevent malicious behavior of a single signatory party, such as constructing virtual voters, etc., we use a multi-party aggregated blind signature scheme based on smart contracts. The registration procedure is shown in Fig. 2.

Assuming there are n voters. First, Voter sets the voting key on the DApp, and the DApp calculates the voting private key and the voting public key . Then, a message is generated, and a random number is selected as a blinding factor. m is blinded using to obtain . Then, is sent to the smart contract along with the identity information of , and the smart contract forwards them to the master node of CA, C and O. After verifying that is a legitimate voter, they use to sign the message to obtain the signature , and then return it to the smart contract. The smart contract gathers these fragments to get BlindSig and returns it to . After receiving BlindSig, unblinds it to obtain the original signature and verifies the correctness of the signature using bpk. Then, sends and Sig to the smart contract. The smart contract verifies the correctness of the signature and the fact that the public key has not been registered and stores on the blockchain. oting initiation stage

During the voting initiation stage, O or can propose a voting proposal to C, including information such as the topic, options, and remarks. Then, members of C will review the proposal; if two-thirds of the members approve it, the proposal will be accepted. After approval, the administrator of C will set additional information, such as the start and end dates of the vote, and send it to the smart contract. The smart contract will verify the initiator’s identity and validate the proposal format. If it passes, the voting information will be published on the blockchain. It allows any authorized voter accessing the blockchain to obtain voting information.
Voting stage

Once voters complete their initial registration, they can vote without the need for repeated registration in subsequent voting. First, will obtain voting information on the blockchain through the DApp and then select his options. The DApp will automatically generate a voting string based on the choice of , which is formatted as shown in Fig. 3. “” represents the options chosen by (, m is the total number of options in that round of voting), connected by the “ &” symbol. “_VOTE_” is the check string for the ballot, used to verify the validity of the format, and finally, there is a randomly generated string of length h ().
Fig. 3
figure 3

Ballot format
Full size image

After the ballot string is generated, the DApp will encode it in ASCII to generate . Next, DApp generates random number , and splits into two parts , then encrypts them to obtain according to Eq. 10.
(10)

Then, enters his voting key , and DApp will generates a random number b, calculates where , and . Finally, DApp will send to the voting smart contract to initiate zero-knowledge proofs. The smart contract will first verify Eq. 11 to prove that owns . After successful verification, the smart contract will store on the blockchain. Then, can verify that his ballot has been stored correctly on the blockchain. The voting procedure is shown in Fig. 4.
(11)
Fig. 4
figure 4

Voting sequence diagram
Full size image
Counting stage

After the voting deadline, if the number of people who have voted is less than two-thirds of the number of people who should have voted, the round of voting will be invalid. If the number of voters exceeds two-thirds, the counting phase begins. Those who did not vote before the deadline will be considered abstaining.

At the beginning of the ballot counting procedure, the smart contract sends all encrypted ballots to all nodes for decryption, and nodes calculate and return corresponding to each ballot to the smart contract according to Eq. 12.
(12)

The smart contract receives and checks , and when the number of correct corresponding to a ballot reaches t, the ballot can be recovered according to Eq. 13.
(13)

The ballot is considered valid if the ballot format is correct, otherwise, it will not be included in the subsequent counting procedure. Finally, the smart contract counts the valid ballots and publishes the counting results on the blockchain.
Scheme analysis

In this section, we will first analyze the security of our proposed smart contract-based aggregated blind signature scheme. Then, the overall voting scheme is evaluated for security using the STRIDE model. Next, the voting scheme is analyzed using the eight security criteria mentioned in the introduction. Finally, the scheme’s outstanding efficiency, versatility, and platform independence will also be analyzed. In addition, Table 2 compares this scheme with other selected blockchain-based e-voting schemes.
Security of smart contract-based aggregated blind signatures
Unforgeability

In this signature scheme, obtaining a complete blind signature requires the joint participation of multiple signing parties and signature aggregation through a smart contract, as shown in Eq. 14.
(14)

From this formula, the problem of unforgeability of the scheme can be statute as the problem of unforgeability of BLS signatures.
Theorem 1

Suppose the hash function H is a random oracle. If exists an adversary A who is able to successfully break the unforgeability of BLS signature scheme in the EU-CMA security model by a non-negligible advantage , then there is a simulator B who is also able to solve the CDH problem in the EU-CMA security model by a non-negligible advantage .
Proof

Given a problem instance over the pairing group PG, B controls the random oracle, runs A, and works as follows.

Initialization phase. Simulator B computes the public key , where a is the private key. The public key is publicly accessible.

Hash query phase. Before receiving a query from A, B chooses a random integer , where refers to the number of hash queries to the random oracle. Then, B creates a empty list to store all queries and responses. Let the i-th hash query be . If is already in , then B will response to this query based on . Otherwise, B chooses at random and sets when , otherwise, . B returns and adds to .

Signature query phase. For a signature query on , if is the -th queried message in , abort. Otherwise, . B computes . According to the definition of BLS signatures, we have
(15)

Therefore, is a valid signature of .

Forging phase. A forges a signature on the non-queried . If is not the -th query message in , abort. Otherwise, . Therefore, we have
(16)

B can calculate as a solution to the CDH problem according to Eq. 17.
(17)

Thus, assuming that A breaks the scheme with advantage after queries in the EU-CMA security model, then B solves the CDH problem with advantage .

In summary, the blind signature scheme is unforgeable.
Blindness

Blindness means that the signer does not know the content of the message when signing. In this scheme, the message blinding equation is
(18)

In this equation, the hash function H is not invertible, as well as the existence of an unknown number r. Therefore, the signer is unable to restore the message m during the signing process.
Untraceability

Untraceability means that when a message-signature pair is publicly available, the signer cannot link the message to the signature record. Suppose there are three signers A, B, and C, each holding signing private keys a, b, and c. The requester sends the blinded message to signer A. A signs to get , and A records . The signature is published when the requester obtains the complete signature and unblinds it. Due to the existence of the random blinding factor r, the signer A is unable to link the signature record to the message by known information. Signers B and C, ditto.
System security

To evaluate the overall security of our proposed voting scheme, we introduced the STRIDE threat modeling methodology to analyze the threats to the system. Threat modeling allows us to identify threats, attacks, and vulnerabilities that may affect the system and thus improve the system design to reduce security risks. The threat modeling data flow diagram is shown in Fig. 5.
Fig. 5
figure 5

Data flow diagram of voting scheme
Full size image

The STRIDE threat report generated from the data flow graph modeling shows that the threats faced by the voting scheme proposed in this paper are spoofing attack, elevation of privilege attack, and denial-of-service (DoS) attack. In addition, the system may be vulnerable to man-in-the-middle and coercive attack.
Spoofing attack

Voters may be spoofed by an attacker to vote on a malicious node. However, in a blockchain system, this scenario requires the malicious node to have more than 51% of the network-wide arithmetic power for this to happen. Therefore, the likelihood is very small.
Denial-of-service (DoS) attack

DOS attack means that the attacker finds a way to make the target node stop providing services. However, in a blockchain system, when one node suffers from a DOS attack, the whole system can still function normally because, it is almost impossible for the attacker to compromise all the nodes.
Elevation of privilege attack

Elevation of privilege attack refers to the possibility that an attacker may be able to illegally access secret data on the system. However, there are strict access control systems in blockchain systems that can effectively prevent elevation of privilege attacks. Even if an attacker breaks through the access control system, the attacker will not be able to get valid information because the secret data has been encrypted or blinded.
Man-in-the-middle (MITM) attack

MIMT attack refers to eavesdropping or tampering with communication data between two parties. In our scheme, an attacker may listen to the communication between the voter and the smart contract during the voting stage to obtain secret information or tamper with the ballot. However, the ballots are encrypted during the communication process. Also, we adopt zero-knowledge proof technique to prevent the leakage of the voter’s private key and incorporate the hash value of the ballot into the zero-knowledge proof process, as shown in Eq. 19.
(19)

Once the ballot has been tampered with, Eq. 20 cannot hold during the zero-knowledge proof process. As a result, it is difficult for the attacker to obtain valuable information from the voting process, and it is impossible to tamper with the ballot.
(20)
Coercive attack

An attacker may be able to coerce a voter into submitting a ballot that he requests. Our scheme is receipt-free, ballots are recorded separately from the voter’s public key, and all ballots are anonymized, making it impossible to link them to the voter’s real identity. Therefore, even if a voter publishes his or her voting public key, an attacker cannot verify the voter’s real ballot.
E-voting fundamental security criteria
Legitimacy
Theorem 2

Only legitimate voting activity can be initiated.
Proof

In our scheme, any voting activity initiated by voters or executing organizations must pass the scrutiny of the voter representative committee(C). Only legitimate voting activities can be approved. The smart contract performs signature verification of the ballot proposal to verify the identity of the ballot sponsor. Only C holds the signature private key, and therefore, only C is authorized to initiate the ballot, ensuring the legitimacy of the voting activity.
Theorem 3

Only successfully registered voters can submit ballots.
Proof

All voters are required to register before submitting a ballot. Voter completes his registration by registering his voting public key on the blockchain, and before he can do so, he needs to be authenticated by the registration authority. However, a dishonest registration authority can influence the outcome of a vote by constructing many fraudulent voters. In this paper, we use our proposed smart contract-based aggregated blind signature scheme. As shown in Eq. 21, the voter must obtain the signature fragments of CA, C, and O to recover the complete signature, which effectively prevents the malicious behavior of a single registration authority.
(21)

Privacy
Theorem 4

No individual or organization, at any stage, can establish a link between the actual identity of the voter and the ballot.
Proof

At the registration stage, our proposed blind signature scheme is utilized to separate the voter’s true identity from their voting public key . From the blindness of the signature scheme proved in Sect. 5.1.2, it follows that when an organization signs a blinded submitted by , although getting ’s identity, it is unable to know the actual being used, thus unable to establish a connection between ’s true identity and his voting public key .

In the voting stage, and the encrypted , verified and passed by the smart contract, will be stored on the blockchain, which all blockchain users can access. From the untraceability of the signature scheme proved in Sect. 5.1.3, it follows that no one can know who the voter corresponding to the is, except for himself. Even if all the ballot contents are decrypted during the counting stage, the voter’s identity is always kept secret since the ballot also does not contain any information about , as shown in Fig. 3.
Integrity
Theorem 5

No one can modify, forge or delete a ballot.
Proof

The ballots submitted by voters are stored on the blockchain, which has the characteristics of decentralization, transparency, and immutability. When there is new data to be added to the blockchain, a consensus is required from all blockchain nodes. All participants will jointly supervise any behavior on the blockchain, making it difficult for anyone to easily modify, forge, or delete ballots.
Fairness
Theorem 6

No one can access the intermediate results of the voting before the end of the voting procedure.
Proof

Before the counting stage begins, all ballots are stored on the blockchain in an encrypted form. If you want to decrypt the ballots in advance, you must get the decryption key. Thanks to adopting the ECC-based threshold encryption scheme for ballots, the security of ballot encryption is significantly enhanced. Decrypting the ballot requires the participation of at least two-thirds of the nodes in the decryption process. Due to the difficulty of solving the discrete logarithmic problem on elliptic curves, the attacker cannot gain access to the system’s private key F(0) through publicly available information such as and . As shown in Eq. 22, the participation of at least t nodes is required to restore the decryption factors .
(22)

Correctness
Theorem 7

All validated legal ballots should be correctly counted in the final results.
Proof

During the ballot decryption process, the computed by all the nodes involved in the decryption can be verified, thereby identifying the spoofers as shown in Eq. 23, ensuring the correctness of the decryption results.
(23)

When counting ballots, the scheme uses blockchain smart contracts to conduct ballot counting, replacing traditional TTP ballot-counting organizations. In blockchain, the deployment of smart contracts must be reviewed by all nodes. The smart contract code related to ballot counting supports public scrutiny by all entities, ensuring that the ballot counting process is open and transparent. Only legally valid ballots that smart contracts have verified will be counted and added to the final results, ensuring the accuracy of the ballot counting results.
Verifiability
Theorem 8

Voters can verify that their ballots were recorded correctly.
Proof

At the time of voting, the encrypted ballot successfully submitted by user is publicly recorded within the blockchain status database. As a result, user can verify his or her ballot on the blockchain at any time.
Theorem 9

Any authorized individuals can verify the final results of the voting.
Proof

After the voting stage, any user with access to the blockchain can use publicly available on the blockchain during the counting stage to decrypt ballots according to Eq. 13. This enables them to verify the correctness of the final ballot counting result independently.
Uniqueness
Theorem 10

Each voter is only allowed to retain one valid ballot for a voting event.
Proof

During the registration stage, the registration node verifies the voter’s identity information and allows them a single chance for a blind signature, resulting in a unique and valid voting public key for each voting round.

During the voting phase, once a voter successfully submits a ballot, the voting public key is stored in the blockchain state database. When the voter uses the again for that round of voting, the smart contract will reject the request. Thus, the scheme guarantees the uniqueness of the ballot.
Robustness
Theorem 11

The system can tolerate a certain number of incorrect ballots without disrupting the voting procedure.
Proof

Even if some voters do not submit their ballots, it will not affect the voting procedure. These non-voting voters will be considered abstentions.

During the ballot counting stage, the smart contract will screen out some invalid ballots through the ballot format verification, and the corresponding voters of these ballots will also be regarded as abstentions. These ballots will not be included in the final result.
Unique features of the scheme
Efficiency

Due to our design of the voting procedure and the addition of smart contract-based aggregate blind signatures and zero-knowledge proofs techniques, our scheme supports asynchronous features:

    The registration and voting stages can be parallelized. After receiving a blind signature from the smart contract, the voter can directly initiate zero-knowledge proofs to the smart contract to vote without waiting for other voters.

    Multiple rounds of voting can be parallelized. This scheme distinguishes the ballots for different voting activities, so multiple rounds of voting can be conducted simultaneously within the same period.

    The voting operation is convenient. After obtaining a one-time identity authentication from the smart contract, the voter can vote multiple times until their identity is revoked. After submitting their ballots, voters can go offline and skip participating in subsequent procedures or frequently interact with other organizations and smart contracts. Therefore, this scheme dramatically simplifies the voting procedure, saves time for voters, and improves voting efficiency. Furthermore, our voting scheme features low latency and high throughput, while also being lightweight and resource-efficient in terms of time and space consumption. Specific experimental data will be presented in the following section.

Versatility

Due to the use of threshold encryption to encrypt the ballot, the content of the ballot is no longer constrained. As a result, we were able to design a ballot format that can support multi-select, which can meet the different needs of various voting scenarios, and can be used not only for democratic elections, but also to support democratic decision-making and polling functions.
Platform independence

This scheme proposes only a secure voting framework without specific requirements for the underlying blockchain structure. Therefore, it is independent of the underlying blockchain platform and can be deployed if it has basic functions including state database and smart contract. Users can choose a suitable blockchain platform based on their security needs, including public blockchains such as Ethereum, EOS, and Solana, consortium blockchains such as Hyperledger Fabric and Hyperchain, or customized private blockchains.
Table 2 Comparison of blockchain-based e-voting scheme
Full size table
