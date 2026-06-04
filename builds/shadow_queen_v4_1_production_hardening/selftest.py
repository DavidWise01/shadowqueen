from shadowqueen.hardening import HardeningKit
r=HardeningKit('.').run_all()
assert r['status']=='PASS', r
print('SELFTEST PASS')
