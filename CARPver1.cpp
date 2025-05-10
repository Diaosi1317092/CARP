#include<bits/stdc++.h>
#define fi first
#define se second
#define mp make_pair
#define pb push_back
typedef long long ll;
typedef long double ld;
using namespace std;
const int N=1010,M=100010,INF=0x3f3f3f3f;
int n,m,m1,m2,p,q,st,val,Q,B,T,g[N][N];
string s[11];
struct edge{int x,y,z,c;};

vector<int> f,vis;
vector<vector<int> > pre;
vector<edge> e,res,tmp;
vector<vector<edge> > ans;

void knapsack(){
	tmp.clear();
	f.resize(Q+1,0);
	vis.resize(Q+1,0);
	vector<vector<int> > pre(e.size()+1,vector<int>(Q+1,-1));	
	for(int i=0;i<(int)e.size();i++)
		for(int j=Q;j>=e[i].c;j--){
			if(f[j-e[i].c]+1>=f[j]){
				f[j]=f[j-e[i].c]+1;
				pre[i][j]=i;
			}
			else pre[i][j]=(i>0?pre[i-1][j]:-1);
		}
	res.clear();
//	cout<<"f: "<<e.size()<<' '<<f[Q]<<'\n';
	for(int i=e.size()-1,j=Q;i>=0&&j>=0&&pre[i][j]>=0;){
		vis[pre[i][j]]=1;
		res.pb(e[pre[i][j]]);	
		j-=e[pre[i][j]].c;
		i=(i==pre[i][j]?i-1:pre[i][j]);
	}
	for(int i=0;i<(int)e.size();i++)
		if(!vis[i])tmp.pb(e[i]);
	e=tmp;
	ans.pb(res);
}

vector<edge> solve(vector<edge> &r){
	p=st;e=r;
	r.clear();
	assert(e.size());
	for(;e.size();){
		sort(e.begin(),e.end(),[](edge a,edge b){
			return min(g[p][a.x],g[p][a.y])+a.z>min(g[p][b.x],g[p][b.y])+b.z;
		});
		edge t=e.back();
		if(g[p][t.x]>g[p][t.y])
			swap(t.x,t.y);
		val+=g[p][t.x]+t.z;
		r.pb(t);
		q-=t.c;
		p=t.y;
		e.pop_back();
	}
	val+=g[p][st];
	return r;
}

int main(){
	
	freopen("egl-s1-A.dat","r",stdin);
//	freopen("sample.txt","w",stdout);
	
//	ios::sync_with_stdio(false);cin.tie(0);cout.tie(0);
	
	cin>>s[1]>>s[2]>>s[3];						// NAME : XXX
	cin>>s[1]>>s[2]>>n;   						// VERTICES : XXX
	cin>>s[1]>>s[2]>>st;						// DEPOT : XXX
	cin>>s[1]>>s[2]>>s[3]>>m1;					// REQUIRED EDGES : XXX
	cin>>s[1]>>s[2]>>s[3]>>m2;					// NON-REQUIRED EDGES : XXX
	cin>>s[1]>>s[2]>>T;							// VEHICLES : XXX
	cin>>s[1]>>s[2]>>Q;							// CAPACITY : XXX	
	cin>>s[1]>>s[2]>>s[3]>>s[4]>>s[5]>>s[6]>>B;	// TOTAL COST OF REQUIRED EDGES : XXX
	cin>>s[1]>>s[2]>>s[3];						// NODES COST DEMAND
	
	m=m1+m2;
	
	memset(g,0x3f,sizeof(g));
	for(int i=1;i<=n;i++)g[i][i]=0;
	
	for(int i=1;i<=m;i++){
		int x,y,z,c;
		cin>>x>>y>>z>>c;
		if(c)e.pb((edge){x,y,z,c});
		g[x][y]=g[y][x]=z;
	}
	
	cin>>s[1];									//END
	
	for(int k=1;k<=n;k++)
		for(int i=1;i<=n;i++)
			for(int j=1;j<=n;j++)
				g[i][j]=min(g[i][j],g[i][k]+g[k][j]);
	
	for(int i=0;i<T&&(int)e.size();i++)knapsack();
	
//	for(vector<edge> t:ans){
//		for(edge ee:t)cout<<"("<<ee.x<<","<<ee.y<<"):";
//		cout<<"\n";
//	}
	
	for(int i=0;i<(int)ans.size();i++)ans[i]=solve(ans[i]);
	
	cout<<"s ";
	
	for(int i=0;i<(int)ans.size();i++){
		cout<<"0,";
		for(edge z:ans[i])
			cout<<"("<<z.x<<","<<z.y<<"),";
		cout<<"0"<<",\n"[i==(int)ans.size()-1];
	}
	
	cout<<"q "<<val<<"\n";
	
	return 0;
}
