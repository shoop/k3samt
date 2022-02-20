# Intel AMT convenience scripts
Recently I procured a couple of SFF machines that I want to use for my homelab
as Kubernetes nodes. The machines were equipped with Intel AMT and seeing as I
intend to manage them without monitor or keyboard attached, I started to look
into this technology.

The [Intel documentation](https://software.intel.com/sites/manageability/AMT_Implementation_and_Reference_Guide/default.htm?turl=WordDocuments%2Fsdkhomepage.htm)
is quite comprehensive, possibly even too much. Even worse, there is next to
no information about managing hosts from a Linux control server. All examples
are either based on (outdated) .NET Framework / C++ code, or on Powershell
examples.

Around the web, others also experimented with this technology:
- Andreas Steinmetz has [an excellent page](https://senseless.info/amt.html)
with his findings, and includes links to [his software](https://senseless.info/downloads.html)
which is a great source of information. While these probably work out of the
box for him, I wanted to understand and customize what was going on and 
unfortunately the main control program was written in bash.
- Gerd Hoffmann wrote [a utility to connect to Serial-over-LAN enabled hosts](https://www.kraxel.org/blog/linux/amtterm/)
(also referred to by Andreas above). I was not yet able to check functionality
but the related `amttool` is unfortunately outdated as it tries to connect
using older technology, not supported by my machines. Also, it was written
in perl.

Therefore I created a couple of python scripts in this repository as
abstractions over the functionality that I need to perform maintenance on these
homelab nodes.
