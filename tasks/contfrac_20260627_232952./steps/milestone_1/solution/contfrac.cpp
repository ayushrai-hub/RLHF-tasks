#include <algorithm>
#include <cmath>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
using namespace std;
typedef __int128 lll;
lll gcdl(lll a,lll b){ if(a<0)a=-a; if(b<0)b=-b; while(b){lll t=b;b=a%b;a=t;} return a; }
string i128s(lll v){ if(v==0)return"0"; bool neg=v<0; unsigned __int128 u=neg?-(unsigned __int128)v:(unsigned __int128)v; string s; while(u){s+=char('0'+(int)(u%10));u/=10;} if(neg)s+='-'; reverse(s.begin(),s.end()); return s; }
lll floordiv(lll a,lll b){ lll q=a/b, r=a%b; if(r!=0 && ((r<0)!=(b<0))) q--; return q; }
string rstr(lll n,lll d){ if(d<0){n=-n;d=-d;} lll g=gcdl(n,d); if(g==0)g=1; n/=g; d/=g; return d==1? i128s(n) : i128s(n)+"/"+i128s(d); }

vector<lll> cfExpand(lll p,lll q){ // q>0
    vector<lll> t; lll a=p,b=q;
    while(b!=0){ lll x=floordiv(a,b); t.push_back(x); lll r=a-x*b; a=b; b=r; }
    return t;
}
// integer sqrt
lll isqrt(lll n){ if(n<0)return -1; lll x=(lll)0; for(lll bit=(lll)1<<62; bit; bit>>=2){} 
    // simple: use long double estimate then adjust
    long double e=sqrtl((long double)n); lll r=(lll)e; while(r>0 && r*r>n) r--; while((r+1)*(r+1)<=n) r++; return r; }

int main(){
    string line;
    while(getline(cin,line)){
        while(!line.empty()&&(line.back()=='\n'||line.back()=='\r')) line.pop_back();
        if(line.empty()) continue;
        istringstream iss(line); vector<string> f; string t; while(iss>>t) f.push_back(t);
        if(f.empty()) continue; string cmd=f[0];
        auto bad=[&](const string&e){ cout<<"ERROR: "<<e<<"\n"; };
        auto pi=[&](const string&s, lll&out)->bool{ try{ size_t pp; long long v=stoll(s,&pp); if(pp!=s.size())return false; out=v; return true; }catch(...){return false;} };
        if(cmd=="CF"||cmd=="LEN"){
            if(f.size()!=3){ bad("usage"); continue; }
            lll p,q; if(!pi(f[1],p)||!pi(f[2],q)){ bad("parse"); continue; }
            if(q<=0){ bad("range"); continue; }
            auto cf=cfExpand(p,q);
            if(cmd=="LEN"){ cout<<cf.size()<<"\n"; }
            else { string r; for(size_t i=0;i<cf.size();i++){ if(i)r+=" "; r+=i128s(cf[i]); } cout<<r<<"\n"; }
        } else if(cmd=="VALUE"){
            if(f.size()<2){ bad("usage"); continue; }
            vector<lll> a; bool ok=true; for(size_t i=1;i<f.size();i++){ lll v; if(!pi(f[i],v)){ok=false;break;} a.push_back(v); }
            if(!ok){ bad("parse"); continue; }
            // fold right to left
            lll vn=a.back(), vd=1;
            for(int i=(int)a.size()-2;i>=0;i--){ if(vn==0){ bad("divzero"); ok=false; break; } lll nn=a[i]*vn+vd; lll nd=vn; vn=nn; vd=nd; }
            if(!ok) continue;
            cout<<rstr(vn,vd)<<"\n";
        } else if(cmd=="CONVERGENT"||cmd=="CONVERGENTS"){
            int need = cmd=="CONVERGENT"?4:3;
            if((int)f.size()!=need){ bad("usage"); continue; }
            lll p,q; if(!pi(f[1],p)||!pi(f[2],q)){ bad("parse"); continue; }
            if(q<=0){ bad("range"); continue; }
            auto cf=cfExpand(p,q);
            // convergents
            vector<pair<lll,lll>> conv; lll hm1=1,hm2=0,km1=0,km2=1;
            for(size_t i=0;i<cf.size();i++){ lll h=cf[i]*hm1+hm2; lll k=cf[i]*km1+km2; conv.push_back({h,k}); hm2=hm1;hm1=h;km2=km1;km1=k; }
            if(cmd=="CONVERGENT"){
                lll kk; if(!pi(f[3],kk)){ bad("parse"); continue; }
                if(kk<0||kk>=(lll)conv.size()){ bad("range"); continue; }
                cout<<rstr(conv[(int)kk].first,conv[(int)kk].second)<<"\n";
            } else {
                string r; for(size_t i=0;i<conv.size();i++){ if(i)r+=" "; r+=rstr(conv[i].first,conv[i].second); } cout<<r<<"\n";
            }
        } else if(cmd=="SQRTCF"||cmd=="PERIOD"||cmd=="PELL"){
            lll n;
            if(cmd=="SQRTCF"){ if(f.size()!=3){ bad("usage"); continue; } }
            else { if(f.size()!=2){ bad("usage"); continue; } }
            if(!pi(f[1],n)){ bad("parse"); continue; }
            if(n<1){ bad("range"); continue; }
            lll a0=isqrt(n);
            bool perfect=(a0*a0==n);
            if(cmd=="SQRTCF"){
                lll k; if(!pi(f[2],k)){ bad("parse"); continue; }
                if(k<1){ bad("range"); continue; }
                vector<lll> terms; terms.push_back(a0);
                if(!perfect){
                    lll m=0,d=1,a=a0;
                    while((lll)terms.size()<k){ m=d*a-m; d=(n-m*m)/d; a=floordiv(a0+m,d); terms.push_back(a); }
                }
                string r; for(size_t i=0;i<terms.size();i++){ if(i)r+=" "; r+=i128s(terms[i]); } cout<<r<<"\n";
            } else if(cmd=="PERIOD"){
                if(perfect){ cout<<"0\n"; continue; }
                lll m=0,d=1,a=a0; lll cnt=0;
                while(true){ m=d*a-m; d=(n-m*m)/d; a=floordiv(a0+m,d); cnt++; if(a==2*a0) break; }
                cout<<i128s(cnt)<<"\n";
            } else { // PELL
                if(perfect){ cout<<"none\n"; continue; }
                // generate sqrt cf terms and convergents until x^2-n y^2=1
                lll m=0,d=1,a=a0;
                lll hm1=a0,hm2=1,km1=1,km2=0; // convergent 0 = a0/1
                // check conv0
                auto check=[&](lll h,lll k)->bool{ return h*h - n*k*k == 1; };
                if(check(hm1,km1)){ cout<<i128s(hm1)<<" "<<i128s(km1)<<"\n"; continue; }
                while(true){
                    m=d*a-m; d=(n-m*m)/d; a=floordiv(a0+m,d);
                    lll h=a*hm1+hm2, k=a*km1+km2;
                    hm2=hm1;hm1=h;km2=km1;km1=k;
                    if(check(h,k)){ cout<<i128s(h)<<" "<<i128s(k)<<"\n"; break; }
                }
            }
        } else bad("unknown command");
    }
    return 0;
}
