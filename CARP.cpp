#include<bits/stdc++.h>
#define fi first
#define se second
#define mp make_pair
#define pb push_back
typedef long long ll;
typedef long double ld;
using namespace std;
const int N=1010,INF=0x3f3f3f3f;
int n,m,m1,m2,p,q,st,val,Q,B,T,g[N][N];
string s[11];
struct edge{
	int x,y,z,c;
};
vector<edge> e;
vector<vector<edge> > ans;

void solve(){
	p=st,q=Q;
	vector<edge> res;
	for(;e.size();){
		sort(e.begin(),e.end(),[](edge a,edge b){
			return min(g[p][a.x],g[p][a.y])<min(g[p][b.x],g[p][b.y]);
		});
		int i=-1;
		for(int j=0;j<(int)e.size();j++)
			if(e[j].c<=q){i=j;break;}
		if(i<0)break;
		if(g[p][e[i].x]>g[p][e[i].y])
			swap(e[i].x,e[i].y);
		val+=g[p][e[i].x]+e[i].z;
		res.pb(e[i]);
		q-=e[i].c;
		p=e[i].y;
		swap(e[i],e.back());
		e.pop_back();
	}
	if(res.size()){
		val+=g[p][st];
		ans.pb(res);
	}
}

int main(){
	
	freopen("egl-s1-A.dat","r",stdin);
	freopen("sample.txt","w",stdout);
	
	ios::sync_with_stdio(false);cin.tie(0);cout.tie(0);
	
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
	
	for(int i=0;i<T;i++)solve();
	
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
