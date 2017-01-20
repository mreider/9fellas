# 9fellas

A simple 12 Factor-based multi-cloud demo application written in Python that visualizes the number of instances currently running with cute animal icons. Application instances register themselves in a shared Redis datastore.

## Commands

- Add fellas by using the /addfella endpoint or by clicking add
- Delete fellas using /deletefella endpoint or by clicking delete

Each line represents an instance of the application, and each instance can host up to 9 fellas.

Application instances send their data to a single public dashboard URL based on the "dashboard" environment variable specified in a manifest file.

## Running 9fellas On Pivotal Web Services

Looking to run 9fellas on Cloud Foundry? Here are some sample instructions for deploying 9fellas onto the hosted Pivotal Web Services cloud:

1. Make sure you have Git installed, available from https://git-scm.com/
2. Make sure your have the Cloud Foundry CF CLI installed, available from http://docs.run.pivotal.io/devguide/installcf/install-go-cli.html
3. Login to your Cloud Foundry cloud. You can sign up for a free trial from http://run.pivotal.io. Once you are signed up, login to your Pivotal Web
Services cloud with:<br/>
   ```
   cf login -a api.run.pivotal.io
   ```
4. Create a new local directory, and clone the 9fellas repo into the new local directory.  From this point on you'll work from your new local directory.<br/>
   ```
   git clone https://github.com/mjeffries-pivotal/9fellas.git
   ```
5. Review the sample xyz-manifest.yml files, where "xyz" represents the IaaS for your targeted Cloud Foundry cloud.  Manifest files are optional but helpful
to specify the metadata for your application.  Samples for **pws** and **openstack** are provided, just copy one of those if you are running on **aws**, **vcd**, or **vsphere**.
6. Update your manifest file to specify the name of the application, replacing "mj" below with your initials or something else to make it unique.  If you've
created a new manifest file, also update the "cloud" value to one of the values mentioned above.  The "dashboard" values should point to the hostname where
you want the consolidated dashboard to run.  The example below is for PWS, where PWS is also hosting the dashboard.

    ```
    ---
    applications:
    - name: 9fellas-mj
     memory: 256M
     instances: 2
     hosts:
     -  9fellas-mj
     -  dashboard-9fellas-mj
     env:
       dashboard: dashboard-9fellas-mj.cfapps.io
       cloud: pws
     services:
     -  redis
     ```

7. Notice that this manifest has two "hosts" values defined.  This is only required for the manifest file associated with the cloud where
the dashboard lives.  All other manifest files do not need the "hosts" section - see the openstack manifest file as an example.
8. Create a shared Redis datastore service. PWS offers a free tier 30mb plan that you can provision with:<br/>
   ```
   cf create-service rediscloud 30mb redis
   ```
  <br/>If you are running on your own Pivotal Cloud Foundry instance, use this instead:<br/>
   ```
   cf create-service p-redis shared-vm redis
   ```
9. Deploy the application using your manifest file using:<br/>
   ```
   cf push -f xyz-manifest.yml
   ```
10. Bring up your application in your browser using the first of the "urls" displayed when the push is completed, for example:<br/>

    ```
    requested state: started
    instances: 2/2
    usage: 256M x 2 instances
    urls: 9fellas-mj.cfapps.io, dashboard-9fellas-mj.cfapps.io
    last uploaded: Fri Mar 18 15:17:02 UTC 2016
    stack: cflinuxfs2
    buildpack: python 1.5.4
    ```

11. Now you can add or delete fellas, and view the dashboard, which will show all the fellas from all the clouds where the application has been installed.
12. Scale the app up to 6 instances to see more animal icons appear using:<br/>

    ```
    cf scale my-app-name -i 6
    ```

  You can also scale the application using the PWS/Apps Manager UI.

Afterwards, tear down your app with:
```
cf apps     # shows all your applications
cf delete my-app-name
cf delete-service redis
cf apps 	# check no apps are found
```
